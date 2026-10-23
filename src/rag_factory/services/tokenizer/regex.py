"""Zero-dependency tokenizer adapter."""

import re


class RegexTokenizer:
    def tokenize(self, text: str) -> list[str]:
        return re.findall(r"\w+", text.casefold())
