import unittest

from littlefox_writing.markup import MarkupBlocked, interpret_html


class MarkupTests(unittest.TestCase):
    def test_structural_text_entities_unicode_and_breaks_are_preserved(self) -> None:
        source = "<p>I &amp; you—틀려.</p><p>typoo<br><br>끝<br></p>\nliteral\u2060line &amp;lt;"
        result = interpret_html(source)
        # The three final newlines retain the trailing <br>, the paragraph
        # boundary, and the literal source newline as three distinct facts.
        expected = "I & you—틀려.\n\ntypoo\n\n끝\n\n\nliteral\u2060line &lt;"
        self.assertEqual(result.rendered_text, expected)
        self.assertEqual(result.correction_text, expected)
        self.assertFalse(result.has_recognized_markup)
        self.assertEqual(result.applied_rules, ())

    def test_supported_synthetic_rules_keep_rendered_and_clean_correction_layers_separate(self) -> None:
        source = (
            '<p>I <span data-lfw-synthetic-rule="struck-deletion">very </span>like it'
            '<span data-lfw-synthetic-rule="empty-insertion-placeholder"></span>.'
            '<span data-lfw-synthetic-rule="empty-punctuation-placeholder" /></p>'
        )
        result = interpret_html(source)
        self.assertEqual(result.rendered_text, "I very like it.")
        self.assertEqual(result.correction_text, "I like it.")
        self.assertTrue(result.has_recognized_markup)
        self.assertEqual(
            result.applied_rules,
            ("empty-insertion-placeholder", "empty-punctuation-placeholder", "struck-deletion"),
        )
        self.assertEqual(result.provenance, "stage2-synthetic-rules-v1")

    def test_entities_are_not_double_unescaped(self) -> None:
        result = interpret_html("Student wrote &amp;lt;tag&amp;gt;.")
        self.assertEqual(result.correction_text, "Student wrote &lt;tag&gt;.")

    def test_incomplete_terminal_fragments_block_but_escaped_less_than_passes(self) -> None:
        malformed = (
            "student <span",
            "student <!-- unfinished",
            "student <!",
            "student <?instruction",
            "student &amp",
        )
        for source in malformed:
            with self.subTest(source=source):
                with self.assertRaises(MarkupBlocked) as caught:
                    interpret_html(source)
                self.assertEqual(caught.exception.code, "malformed_html")
        self.assertEqual(
            interpret_html("Student wrote 2 &lt; 3.").correction_text,
            "Student wrote 2 < 3.",
        )

    def test_empty_placeholders_reject_structural_children_but_allow_genuine_empty(self) -> None:
        for rule in ("empty-insertion-placeholder", "empty-punctuation-placeholder"):
            with self.subTest(rule=rule, case="structural"):
                with self.assertRaises(MarkupBlocked) as caught:
                    interpret_html(f'<span data-lfw-synthetic-rule="{rule}"><br></span>')
                self.assertEqual(caught.exception.code, "nonempty_placeholder")
            with self.subTest(rule=rule, case="empty"):
                result = interpret_html(f'before<span data-lfw-synthetic-rule="{rule}"></span>after')
                self.assertEqual(result.correction_text, "beforeafter")
                self.assertTrue(result.has_recognized_markup)

    def test_case_and_other_unverified_rules_block(self) -> None:
        for rule in ("case", "spelling", "word-form", "word-replacement", "insert-word", "undo-reset"):
            with self.subTest(rule=rule):
                with self.assertRaises(MarkupBlocked) as caught:
                    interpret_html(f'<span data-lfw-synthetic-rule="{rule}">word</span>')
                self.assertEqual(caught.exception.code, "unsupported_correction_rule")

    def test_unknown_semantics_nonempty_placeholder_and_nesting_block(self) -> None:
        samples = (
            '<span style="color:red">text</span>',
            '<span data-lfw-synthetic-rule="future-rule">text</span>',
            '<span data-lfw-synthetic-rule="empty-insertion-placeholder">student text</span>',
            '<span data-lfw-synthetic-rule="struck-deletion"><span data-lfw-synthetic-rule="struck-deletion">x</span></span>',
            "<p><strong>broken</p>",
            "<script>unknown</script>",
            "<?unknown instruction?>",
        )
        for source in samples:
            with self.subTest(source=source):
                with self.assertRaises(MarkupBlocked):
                    interpret_html(source)


if __name__ == "__main__":
    unittest.main()

