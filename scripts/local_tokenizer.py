from lightrag.utils import Tokenizer


class CharTokenizer:
    def encode(self, content: str) -> list[int]:
        return [ord(char) for char in content or ""]

    def decode(self, tokens: list[int]) -> str:
        return "".join(chr(int(token)) for token in tokens)


LOCAL_TOKENIZER = Tokenizer("char-tokenizer", CharTokenizer())
