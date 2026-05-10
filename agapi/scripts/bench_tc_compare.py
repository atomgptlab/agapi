"""Compare AGAPIAgent with vs without tool calling on Tc_supercon (50 entries)."""
import re, json, time
import numpy as np
from sklearn.metrics import mean_absolute_error, r2_score
from jarvis.db.figshare import data
from agapi.agents import AGAPIAgent

API_KEY = "sk-"
PROP_KEY = "Tc_supercon"
PROP_NAME = "superconducting Tc"
UNIT = "K"
MAX_N = 50

NUM_RE = re.compile(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?")

def parse_num(s):
    if not s:
        return float("nan")
    s = str(s)
    # prefer last number in the string (final answer usually trails)
    nums = NUM_RE.findall(s)
    return float(nums[-1]) if nums else float("nan")

def make_prompt(formula, prop, unit):
    return (
        f"Estimate the {prop} of {formula} in {unit}. "
        f"Respond with ONLY a single number (e.g. '3.7'). "
        f"No words, no units, no apologies."
    )

def query(agent, formula, use_tools):
    prompt = make_prompt(formula, PROP_NAME, UNIT)
    for attempt in range(2):
        try:
            txt = agent.query_sync(
                prompt,
                use_tools=use_tools,
                verbose=False,
                render_html=False,
            )
        except Exception as e:
            print(f"   [err attempt {attempt}] {e}")
            txt = ""
        val = parse_num(txt)
        if val == val:
            return val, txt
    return float("nan"), txt

def main():
    print("Loading dft_3d...")
    dat = data("dft_3d")
    print(f"Loaded {len(dat)} entries")

    # collect first MAX_N entries with valid Tc_supercon
    samples = []
    for i in dat:
        v = i.get(PROP_KEY)
        if v in (None, "na", "", "None"):
            continue
        try:
            truth = float(v)
        except (TypeError, ValueError):
            continue
        samples.append((i.get("jid"), i["formula"], truth))
        if len(samples) >= MAX_N:
            break
    print(f"Selected {len(samples)} samples")

    agent = AGAPIAgent(api_key=API_KEY)

    results = {"base": [], "tools": []}
    for mode in ("base", "tools"):
        use_tools = (mode == "tools")
        print(f"\n=== Running mode={mode} (use_tools={use_tools}) ===")
        for k, (jid, formula, truth) in enumerate(samples):
            t0 = time.time()
            val, raw = query(agent, formula, use_tools)
            dt = time.time() - t0
            print(f"[{mode} {k+1}/{len(samples)}] {formula:20s} truth={truth:7.3f}  pred={val:8.3f}  ({dt:.1f}s)")
            results[mode].append({
                "jid": jid, "formula": formula,
                "truth": truth,
                "pred": None if val != val else val,
                "raw": (raw[:200] if isinstance(raw, str) else str(raw)[:200]),
                "elapsed_s": dt,
            })
            # incremental dump in case of crash
            with open(f"results_{PROP_KEY}_{mode}.json", "w") as f:
                json.dump({"property": PROP_KEY, "mode": mode, "entries": results[mode]}, f, indent=2)

    # metrics
    summary = {}
    for mode in ("base", "tools"):
        ent = results[mode]
        x = np.array([e["pred"] if e["pred"] is not None else float("nan") for e in ent])
        y = np.array([e["truth"] for e in ent])
        mask = ~np.isnan(x)
        if mask.sum() >= 2:
            mae = mean_absolute_error(y[mask], x[mask])
            r2 = r2_score(y[mask], x[mask])
        else:
            mae, r2 = float("nan"), float("nan")
        cov = int(mask.sum()) / len(x) if len(x) else 0.0
        summary[mode] = {"mae": mae, "r2": r2, "coverage": cov, "n": len(x), "n_parsed": int(mask.sum())}
        print(f"\n{mode:5s}: MAE={mae:.3f}  R^2={r2:.3f}  coverage={mask.sum()}/{len(x)} ({cov:.0%})")

    with open(f"results_{PROP_KEY}_compare_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("\n=== FINAL ===")
    print(json.dumps(summary, indent=2))
    if not np.isnan(summary["base"]["mae"]) and not np.isnan(summary["tools"]["mae"]):
        winner = "tools" if summary["tools"]["mae"] < summary["base"]["mae"] else "base"
        print(f"\nLower MAE: {winner}")

if __name__ == "__main__":
    main()
