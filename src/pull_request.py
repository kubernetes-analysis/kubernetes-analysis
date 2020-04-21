import re
from typing import Dict, Optional

from .issue import Issue

RELEASE_NOTE_REGEX = re.compile(
    r"\s*[/\"']?`*\s*(?:release[-\s]note[s]?[-:\s]?)?\s*(none|n/a|na|TODO)",
    re.IGNORECASE)


class PullRequest(Issue):
    __release_note: Optional[str]

    def __init__(self, data: Dict):
        super().__init__(data)
        self.__release_note = self.__extract_release_note()

    @property
    def release_note(self) -> Optional[str]:
        return self.__release_note

    @release_note.setter
    def release_note(self, value: str):
        self.__release_note = value

    def __extract_release_note(self) -> Optional[str]:
        if not self.markdown:
            return None

        # extract the release note block
        res = []
        parse = False
        for line in self.markdown.splitlines():
            if parse and line == "```":
                break
            if parse:
                res.append(line)
            if line.startswith("```release-note"):
                parse = True

        # filter NONEs
        joined = "".join(res).strip()
        if joined and not re.match(RELEASE_NOTE_REGEX, joined):
            note = "\n".join(res).strip()
            prefix = "- "
            if note.startswith(prefix):
                note = note[len(prefix):]
            return note

        return None
