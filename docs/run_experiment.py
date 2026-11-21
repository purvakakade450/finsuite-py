import json, os, sys, time
os.environ["FINSUITE_NO_ENV_FILE"] = "1"
sys.path.insert(0, os.getcwd())
from app import predict

SYMBOLS = [("RELIANCE.NS", "Reliance Industries"), ("TCS.NS", "Tata Consultancy Services"), ("^NSEI", "NIFTY 50 index"), ("AAPL", "Apple Inc.")]
out = {}
for sym, name in SYMBOLS:
    t = time.time()
    d = predict.predict_next_close(sym, "5y")
    out[sym] = {"name": name, "days": d["data"]["days"], "usable": d["data"]["usable"], "train": d["data"]["train"], "test": d["data"]["test"],
                "metrics": d["metrics"], "direction": d["direction_accuracy"], "best": d["best_model"], "beats": d["beats_baseline"],
                "walk": d["walk_forward"], "currency": d["currency"], "seconds": round(time.time() - t, 1)}
    print(sym, "ok", out[sym]["seconds"], "s", "days", d["data"]["days"], flush=True)
open(sys.argv[1], "w", encoding="utf-8").write(json.dumps(out, indent=1, ensure_ascii=False))
