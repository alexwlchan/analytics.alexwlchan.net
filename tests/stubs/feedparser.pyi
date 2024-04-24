import typing

class Feed(typing.TypedDict):
    entries: list[dict[str, str]]

def parse(text: str) -> Feed: ...
