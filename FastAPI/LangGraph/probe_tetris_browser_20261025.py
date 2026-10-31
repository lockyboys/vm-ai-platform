"""Read-only availability probe for real-browser Tetris verification."""
import importlib.util,json,shutil
def main():
    print(json.dumps({"executables":{n:shutil.which(n) for n in ("chromium","chromium-browser","google-chrome","firefox")},
                      "python_packages":{n:importlib.util.find_spec(n) is not None for n in ("playwright","selenium")}}))
if __name__=="__main__":main()
