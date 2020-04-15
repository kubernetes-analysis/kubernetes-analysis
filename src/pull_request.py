import re
from typing import Dict, Optional

from .bag_of_words import BagOfWords
from .issue import Issue

RELEASE_NOTE_REGEX = re.compile(
    r"\s*[/\"']?`*\s*(?:release[-\s]note[s]?[-:\s]?)?\s*(none|n/a|na|TODO)",
    re.IGNORECASE)


class PullRequest(Issue):
    __release_note: Optional[str]
    __release_note_bag_of_words: Optional[BagOfWords]

    def __init__(self, data: Dict, enable_nlp=False):
        super().__init__(data)

        self.__release_note = None
        self.__release_note_bag_of_words = None

        if enable_nlp:
            self.__extract_release_note()
            self.__release_note_bag_of_words = BagOfWords(self.release_note)

    @property
    def release_note(self) -> Optional[str]:
        return self.__release_note

    @property
    def release_note_bag_of_words(self) -> Optional[BagOfWords]:
        return self.__release_note_bag_of_words

    def __extract_release_note(self):
        if not self.markdown:
            return

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
            self.__release_note = note
