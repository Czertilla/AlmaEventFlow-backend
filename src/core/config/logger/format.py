from logging import CRITICAL, DEBUG, ERROR, INFO, WARNING

from colorama import Back, Fore, Style


def cb(x: str) -> str:
    return Fore.BLUE + x + Fore.RESET


def cg(x: str) -> str:
    return Fore.GREEN + x + Fore.RESET


def cr(x: str) -> str:
    return Fore.RED + x + Fore.RESET


def cc(x: str) -> str:
    return Fore.CYAN + x + Fore.RESET


def cy(x: str) -> str:
    return Fore.YELLOW + x + Fore.RESET


def cm(x: str) -> str:
    return Fore.MAGENTA + x + Fore.RESET


def br(x: str) -> str:
    return Back.RED + x + Back.RESET


c_ = Fore.RESET
s_ = Style.RESET_ALL


def sb(x: str) -> str:
    return Style.BRIGHT + x + Style.NORMAL


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
