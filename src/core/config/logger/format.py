from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL
from colorama import Fore, Style, Back

cb = lambda x: Fore.BLUE + x + Fore.RESET  # noqa: E731
cg = lambda x: Fore.GREEN + x + Fore.RESET  # noqa: E731
cr = lambda x: Fore.RED + x + Fore.RESET  # noqa: E731
cc = lambda x: Fore.CYAN + x + Fore.RESET  # noqa: E731
cy = lambda x: Fore.YELLOW + x + Fore.RESET  # noqa: E731
cm = lambda x: Fore.MAGENTA + x + Fore.RESET  # noqa: E731
br = lambda x: Back.RED + x + Back.RESET  # noqa: E731
c_ = Fore.RESET
s_ = Style.RESET_ALL
sb = lambda x: Style.BRIGHT + x + Style.NORMAL  # noqa: E731
act = cg("%(asctime)s")
prc = f"[{cc('%(process)s')}]"
lvl = "%(levelname)-8s"
loc = f"{cm('%(name)s')}:{cb('%(funcName)s')}:{cc('%(lineno)s')}"
msg = "%(message)s"
exc = cr("%(exc_info)s")
err_id = cm("%(err_id)s")

FORMATS = {
    DEBUG: f"{act} {prc} {cb(lvl)} | {loc} - {msg}",
    INFO: f"{act} {prc} {cg(lvl)} | {loc} - {msg}",
    WARNING: f"{act} {prc} {cy(lvl)} | {loc} - {cy(msg)}",
    ERROR: f"{act} {prc} {cr(lvl)} | {loc} - {cr(msg)} |{err_id}| {exc}",
    CRITICAL: f"{act} {prc} {sb(br(lvl))} | {loc} - {sb(cr(msg))} |{err_id}| {exc}",
}
