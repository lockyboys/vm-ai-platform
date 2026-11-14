"""Verify the self-contained Tetris game in an existing Playwright Chromium.
Never installs browsers, accesses user sessions, or visits external sites.
"""
import hashlib
import json
from pathlib import Path
def main():
    from playwright.sync_api import sync_playwright
    source=Path("haness/apps/tetris_combined_chromium_20261026/tetris.html")
    report={"passed":[],"page_errors":[],"source_sha256":hashlib.sha256(source.read_bytes()).hexdigest()}
    with sync_playwright() as p:
        executable=Path(p.chromium.executable_path)
        report["executable_available"]=executable.exists()
        if not executable.exists():
            print(json.dumps(report));return
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        try:
            page=browser.new_page(viewport={"width":1100,"height":1000})
            page.on("pageerror",lambda error:report["page_errors"].append(str(error)))
            page.goto(source.resolve().as_uri())
            assert page.title()=="BLOCK / 테트리스";report["passed"].append("offline load")
            page.locator("#start").click()
            assert page.locator("#overlay").is_hidden();report["passed"].append("start")
            page.evaluate("game.active={type:'T',shape:[[0,1,0],[1,1,1]],x:3,y:3};render()")
            page.locator("#board").click();page.keyboard.press("ArrowLeft")
            assert page.evaluate("game.active.x")==2;report["passed"].append("keyboard movement")
            page.keyboard.press("ArrowUp")
            assert page.evaluate("game.active.shape.length")==3;report["passed"].append("rotation")
            page.keyboard.press("p");assert page.evaluate("game.paused")
            x=page.evaluate("game.active.x");page.keyboard.press("ArrowRight")
            assert page.evaluate("game.active.x")==x;report["passed"].append("pause blocks input")
            page.locator("#start").click();assert not page.evaluate("game.paused")
            report["passed"].append("resume")
            page.keyboard.press("Space")
            assert page.evaluate("game.board.flat().filter(Boolean).length")==4
            report["passed"].append("hard drop")
            page.locator("#restart").click();assert page.evaluate("game.score")==0
            page.keyboard.press("Space")
            assert page.evaluate("game.board.flat().filter(Boolean).length")==4
            report["passed"].append("restart restores keyboard focus")
            page.locator("#restart").click();page.locator("[data-action=right]").click()
            page.keyboard.press("Space")
            assert page.evaluate("game.board.flat().filter(Boolean).length")==4
            report["passed"].append("touch button restores keyboard focus")
            page.locator("#restart").click();page.locator("#pause").click();page.locator("#pause").click()
            page.keyboard.press("Space")
            assert page.evaluate("game.board.flat().filter(Boolean).length")==4
            report["passed"].append("pause button restores keyboard focus")
            page.evaluate("game.gameOver=true;render()")
            assert page.locator("#overlay-title").inner_text()=="GAME OVER"
            page.locator("#start").click();assert not page.evaluate("game.gameOver")
            report["passed"].append("game over and retry")
            report["layouts"]=[]
            for width in (320,360,390,480,768,1100):
                page.set_viewport_size({"width":width,"height":844})
                metrics=page.evaluate("({viewport:innerWidth,scroll:document.documentElement.scrollWidth})")
                assert metrics["scroll"]<=metrics["viewport"],str(metrics)
                assert page.locator("#board").bounding_box()["width"]>100
                report["layouts"].append(metrics)
                report["passed"].append("layout "+str(width))
            page.set_viewport_size({"width":320,"height":844})
            page.evaluate("game.score=999999999;render()")
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
            report["passed"].append("large mobile score wraps")
            report["browser_version"]=browser.version
            assert not report["page_errors"]
            report["passed"].append("no page errors")
        except Exception as error:
            report["error"]=str(error)
            report["error_type"]=type(error).__name__
            report["diagnostics"]=page.evaluate("({viewport:innerWidth,scroll:document.documentElement.scrollWidth,elements:[...document.querySelectorAll('main,header,.layout,.board-shell,#board,.touch,aside,.card,footer')].map(e=>({name:e.id||e.className||e.tagName,x:e.getBoundingClientRect().x,width:e.getBoundingClientRect().width,right:e.getBoundingClientRect().right,scroll:e.scrollWidth}))})")
            report["browser_version"]=browser.version
        finally:browser.close()
    path=Path("harness/memory/tetris_combined_chromium_20261026.json")
    # Preserve the evidence even when the runner starts in a clean workspace.
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({**report,"evidence":str(path)},ensure_ascii=False))
if __name__=="__main__":main()
