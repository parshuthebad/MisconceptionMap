"""Measure how often the AI finds the right first-error step.
Put photos in eval/samples/ and labels in eval/labels.csv:  filename,first_error_step   (use 0 for 'no error')
Run: python eval/run_eval.py   (server must be running on :8000 with a real API key)"""
import csv, pathlib, requests

root = pathlib.Path(__file__).parent
hit = n = 0
for row in csv.DictReader(open(root / "labels.csv")):
    with open(root / "samples" / row["filename"], "rb") as f:
        r = requests.post("http://localhost:8000/api/analyze", files={"image": f}, data={"language": "en"}).json()
    got = r.get("first_error_step") or 0
    ok = got == int(row["first_error_step"])
    hit += ok; n += 1
    print(f"{row['filename']:30} expected={row['first_error_step']} got={got} {'OK' if ok else 'MISS'}")
print(f"\nError-step accuracy: {hit}/{n} = {100*hit/max(n,1):.0f}%")
