"""Real Chromium verification for the offline scientific calculator."""
import json,math
from pathlib import Path
def main():
    from playwright.sync_api import sync_playwright
    report={"passed":[],"page_errors":[]}
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        page=browser.new_page(viewport={"width":1100,"height":1000})
        page.on("pageerror",lambda error:report["page_errors"].append(str(error)))
        current="load"
        try:
            page.goto(Path("haness/apps/scientific_calculator_20261025/scientific_calculator.html").resolve().as_uri())
            assert page.title()=="VECTOR / 공학용 계산기";report["passed"].append("offline load")
            def calculate(expression,expected,label):
                nonlocal current
                current=label
                page.locator("#expression").fill(expression);page.locator("#expression").press("Enter")
                actual=float(page.locator("#result").inner_text())
                assert math.isclose(actual,expected,rel_tol=1e-10,abs_tol=1e-10),(expression,actual,expected)
                report["passed"].append(label)
            calculate("sin(30)+sqrt(16)",4.5,"degree scientific expression")
            calculate("2^3^2",512,"right-associative power")
            calculate("-2^2",-4,"unary precedence")
            calculate("5!",120,"factorial")
            calculate("log(8,2)",3,"log with base")
            calculate("50%",.5,"percentage")
            page.locator("#rad").click();calculate("sin(pi/2)",1,"radian mode")
            calculate("asin(1)",math.pi/2,"inverse radian")
            page.locator("#deg").click();calculate("asin(0.5)",30,"inverse degree")
            current="zero division error"
            page.locator("#expression").fill("1/0");page.locator("#equals").click()
            assert page.locator("#result").inner_text()=="오류";report["passed"].append(current)
            page.locator('[data-insert="7"]').click();page.locator("#expression").press("Enter")
            assert page.locator("#result").inner_text()=="7";report["passed"].append("digit recovery after error")
            page.locator("#clear").click();page.locator("#ans").click()
            page.locator('[data-insert="*"]').click();page.locator('[data-insert="2"]').click()
            page.locator("#equals").click();assert page.locator("#result").inner_text()=="14"
            report["passed"].append("answer memory")
            page.locator("#clear").click()
            for value in ("7","+","8"):page.locator('[data-insert="'+value+'"]').click()
            page.locator("#equals").click();assert page.locator("#result").inner_text()=="15"
            report["passed"].append("button expression")
            page.locator("#expression").fill("12345")
            page.locator("#expression").evaluate("(e)=>e.setSelectionRange(1,4)")
            page.locator('[data-insert="9"]').click()
            assert page.locator("#expression").input_value()=="195"
            report["passed"].append("selected text replacement")
            page.locator("#expression").fill("12345")
            page.locator("#expression").evaluate("(e)=>e.setSelectionRange(1,4)")
            page.locator("#backspace").click();assert page.locator("#expression").input_value()=="15"
            report["passed"].append("selected text deletion")
            current="backspace clears stale error"
            page.locator("#expression").fill("1/0");page.locator("#equals").click();page.locator("#backspace").click()
            assert page.locator("#result").inner_text()=="0"
            report["passed"].append(current)
            page.locator("#deg").click();calculate("sin(30)",.5,"history degree entry")
            page.locator("#rad").click();calculate("sin(pi/2)",1,"history radian entry")
            page.locator(".history-item").nth(1).click()
            assert page.locator("#deg").get_attribute("aria-pressed")=="true"
            assert page.locator("#result").inner_text()=="0.5";report["passed"].append("history restores angle mode")
            for value in range(7):calculate(str(value),value,"history append "+str(value))
            assert page.locator(".history-item").count()==5;report["passed"].append("bounded history")
            page.locator("#expression").press("Escape")
            assert page.locator("#expression").input_value()=="";assert page.locator("#result").inner_text()=="0"
            report["passed"].append("Escape clear")
            page.locator('[data-insert="sin("]').focus();page.locator('[data-insert="sin("]').press("Enter")
            assert page.locator("#expression").input_value()=="sin(";report["passed"].append("keyboard button activation")
            calculate("170!",7.257415615307994e306,"large result")
            report["layouts"]=[]
            for width in (320,360,390,480,768,1100):
                current="layout "+str(width)
                page.set_viewport_size({"width":width,"height":844})
                metrics=page.evaluate("({viewport:innerWidth,scroll:document.documentElement.scrollWidth})")
                assert metrics["scroll"]<=metrics["viewport"],metrics
                report["layouts"].append(metrics);report["passed"].append(current)
            assert not report["page_errors"];report["passed"].append("no page errors")
        except Exception as error:
            report.update(failed_check=current,error_type=type(error).__name__,error=str(error))
        finally:
            report["browser_version"]=browser.version;browser.close()
    path=Path("harness/memory/scientific_calc_browser_20261025.json")
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({**report,"evidence":str(path)},ensure_ascii=False))
if __name__=="__main__":main()
