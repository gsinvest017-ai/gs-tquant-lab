# Progress: Convert all `.ipynb` to `.py`

## 目標
把 TQuant-Lab 內所有 Jupyter notebook（`.ipynb`）轉成同名 `.py`，放在原檔旁邊，方便 grep、diff、IDE 編輯與 CI 跑語法檢查。輸出資料不嵌入，magics 註解掉以保持 `.py` 可被 import / py_compile。

## 計畫 milestone

- **M1** — 寫 stdlib-only 轉換器 `tools/ipynb_to_py.py`（無 nbformat 依賴，因系統 Python 受 PEP 668 鎖）
- **M2** — 對全 repo 跑一次，產生 77 個 `.py` 檔
- **M3** — Spot-check 4 個輸出檔的語法 + commit
- **M4** — 寫 `tools/check_converted_py.py` 並對全部 77 個輸出跑全量 py_compile + magic-leak 檢查

## 進度日誌

### M1 — 轉換器
- 寫了 `tools/ipynb_to_py.py`：把 ipynb（純 JSON）逐 cell 轉出
  - code cell → 原樣輸出
  - markdown / raw cell → `# ` 前綴註解
  - magics (`!`, `%`, `?`) → 註解掉，避免 `py_compile` 噴 syntax error
  - 每個 cell 前加 `# %% [kind] cell N` 標記（VS Code / PyCharm 認得，可當 cell 切分）
- 為什麼不裝 jupytext / nbconvert：系統 Python 是 externally-managed，`pip install` 被擋；conda 沒裝；用 stdlib 最乾淨

### M2 — 全 repo 轉檔
- `python3 tools/ipynb_to_py.py .` → `Converted 77/77 notebooks.`，零錯誤
- 涵蓋目錄：`./Aroon.ipynb`、`Problem/` (6)、`example/` (39)、`lecture/` (31)

### M3 — Spot-check
- `python3 -m py_compile` 跑過 4 個樣本（含中英檔名、含 `!zipline ingest` magic、含長 markdown 區塊）全部通過
- 確認 markdown 正確變成 `#` 註解、import 清單完整、`!zipline` 已註解化

### M4 — 全量驗證腳本
- 寫了 `tools/check_converted_py.py`（stdlib-only，配對 .ipynb / .py 後跑兩道檢查）：
  - **py_compile**：抓 syntax error，能擋住未註解的 magic 或殘留 markdown
  - **Magic-leak 掃描**：用 regex `^[!%?]` 找漏網的 IPython 指令
- 對全 repo 跑：`OK 77/77`、`Missing 0`、`Compile failures 0`、`Magic leaks 0`
- 統計：30,251 行、2,092 個 cell marker
- Exit code 0 — 可直接接 CI；exit 2 代表有 leak/失敗
- 用法：
  ```bash
  python3 tools/check_converted_py.py           # 預設掃當前目錄
  python3 tools/check_converted_py.py --quiet   # 只印 summary
  python3 tools/check_converted_py.py lecture   # 只掃子目錄
  ```

## Fallback 指引

若要回退：
```bash
# 刪掉所有產生的 .py（保留原 ipynb 與工具）
find . -name "*.py" -not -path "./tools/*" -newer tools/ipynb_to_py.py -delete
```

若要重跑：
```bash
python3 tools/ipynb_to_py.py .
```

若要只轉某個子目錄：
```bash
python3 tools/ipynb_to_py.py lecture
```

## 已知限制 / 後續

- 沒處理 cell outputs（刻意丟掉，保持 .py 乾淨）
- magics 一律註解；若 `.py` 要直接執行（不是 import），自行把 `# !zipline ingest` 還原成 shell call
- 若日後 ipynb 更新，須手動重跑轉換器；可考慮加 pre-commit hook
