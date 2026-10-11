"""Conservative offline HTML interpretation using synthetic rule signatures.

The ``data-lfw-synthetic-rule`` attribute is a Stage 2 fixture convention. It
is not claimed to occur on Little Fox. Real signatures require later approved
validation before they can be added to this registry.
"""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser


@dataclass(frozen=True, slots=True)
class MarkupResult:
    rendered_text: str
    correction_text: str
    has_recognized_markup: bool
    applied_rules: tuple[str, ...]
    provenance: str = "stage2-synthetic-rules-v1"


class MarkupBlocked(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(slots=True)
class _TextBuilder:
    parts: list[str]
    paragraph_pending: bool = False

    def text(self, value: str) -> None:
        if not value:
            return
        if self.paragraph_pending:
            if self.parts:
                trailing = len(self.parts[-1]) - len(self.parts[-1].rstrip("\n"))
                self.parts.append("\n" * max(0, 2 - trailing))
            self.paragraph_pending = False
        self.parts.append(value)

    def line_break(self) -> None:
        if self.paragraph_pending:
            if self.parts:
                trailing = len(self.parts[-1]) - len(self.parts[-1].rstrip("\n"))
                self.parts.append("\n" * max(0, 2 - trailing))
            self.paragraph_pending = False
        self.parts.append("\n")

    def paragraph(self) -> None:
        self.paragraph_pending = True

    def finish(self) -> str:
        return "".join(self.parts)


_INLINE_TAGS = {"span", "strong", "em", "b", "i"}
_BLOCK_TAGS = {"p", "div"}
_SUPPORTED_RULES = {
    "struck-deletion": "omit-visible-content",
    "empty-insertion-placeholder": "omit-empty-element",
    "empty-punctuation-placeholder": "omit-empty-element",
}
_UNSUPPORTED_RULES = {
    "case",
    "erase",
    "spelling",
    "word-form",
    "word-replacement",
    "insert-word",
    "punctuation",
    "undo-reset",
}


class _ConservativeHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rendered = _TextBuilder([])
        self.correction = _TextBuilder([])
        self.stack: list[tuple[str, str | None]] = []
        self.active_rule: str | None = None
        self.active_rule_had_data = False
        self.recognized = False
        self.rules: set[str] = set()

    @property
    def omitting(self) -> bool:
        return self.active_rule is not None

    def _block(self, code: str, detail: str) -> None:
        raise MarkupBlocked(code, detail)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self.active_rule is not None and self.active_rule.startswith("empty-"):
            self._block(
                "nonempty_placeholder",
                f"Placeholder rule contains structural markup: {self.active_rule}",
            )
        if tag == "br":
            if attrs:
                self._block("unsupported_attributes", "Attributes on <br> are not supported")
            self.rendered.line_break()
            if not self.omitting:
                self.correction.line_break()
            return
        if tag not in _INLINE_TAGS | _BLOCK_TAGS:
            self._block("unsupported_tag", f"Unsupported HTML tag: <{tag}>")
        if tag in _BLOCK_TAGS:
            if attrs:
                self._block("unsupported_attributes", f"Attributes on <{tag}> are not supported")
            self.rendered.paragraph()
            if not self.omitting:
                self.correction.paragraph()
            self.stack.append((tag, None))
            return

        rule: str | None = None
        if attrs:
            if tag != "span" or len(attrs) != 1 or attrs[0][0].lower() != "data-lfw-synthetic-rule" or attrs[0][1] is None:
                self._block("unknown_semantic_markup", f"Unsupported attributes on <{tag}>")
            rule = attrs[0][1]
            self.recognized = True
            if self.active_rule is not None:
                self._block("nested_annotation", "Nested correction annotations are ambiguous")
            if rule in _UNSUPPORTED_RULES:
                self._block("unsupported_correction_rule", f"Correction rule is not safely supported: {rule}")
            if rule not in _SUPPORTED_RULES:
                self._block("unknown_correction_rule", f"Unknown correction rule: {rule}")
            self.active_rule = rule
            self.active_rule_had_data = False
            self.rules.add(rule)
        self.stack.append((tag, rule))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "br":
            self._block("malformed_html", "Closing </br> is not supported")
        if not self.stack or self.stack[-1][0] != tag:
            self._block("malformed_html", f"Unbalanced closing tag: </{tag}>")
        _, rule = self.stack.pop()
        if rule is not None:
            if rule.startswith("empty-") and self.active_rule_had_data:
                self._block("nonempty_placeholder", f"Placeholder rule contains visible text: {rule}")
            self.active_rule = None
            self.active_rule_had_data = False
        if tag in _BLOCK_TAGS:
            self.rendered.paragraph()
            if not self.omitting:
                self.correction.paragraph()

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "br":
            self.handle_starttag(tag, attrs)
            return
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        self.rendered.text(data)
        if self.active_rule is not None:
            if data:
                self.active_rule_had_data = True
            return
        self.correction.text(data)

    def handle_comment(self, data: str) -> None:
        self._block("unsupported_markup", "HTML comments are not supported")

    def handle_decl(self, decl: str) -> None:
        self._block("unsupported_markup", "HTML declarations are not supported")

    def unknown_decl(self, data: str) -> None:
        self._block("unsupported_markup", "Unknown HTML declarations are not supported")

    def handle_pi(self, data: str) -> None:
        self._block("unsupported_markup", "Processing instructions are not supported")

    def finish(self) -> MarkupResult:
        if self.stack:
            self._block("malformed_html", f"Unclosed HTML tag: <{self.stack[-1][0]}>")
        return MarkupResult(
            rendered_text=self.rendered.finish(),
            correction_text=self.correction.finish(),
            has_recognized_markup=self.recognized,
            applied_rules=tuple(sorted(self.rules)),
        )


def interpret_html(source_html: str) -> MarkupResult:
    """Interpret supported HTML once; entities are unescaped exactly once."""
    parser = _ConservativeHtmlParser()
    try:
        parser.feed(source_html)
        # HTMLParser.close() converts some unfinished terminal constructs into
        # ordinary data. Inspect its pending buffer first so truncated tags,
        # comments, declarations and entities cannot become exportable text.
        if parser.rawdata:
            raise MarkupBlocked("malformed_html", "Incomplete terminal HTML fragment")
        parser.close()
        return parser.finish()
    except MarkupBlocked:
        raise
    except Exception as error:  # HTMLParser can surface malformed entity errors.
        raise MarkupBlocked("malformed_html", str(error)) from error

