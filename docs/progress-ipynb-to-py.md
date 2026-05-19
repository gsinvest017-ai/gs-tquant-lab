# Progress: Convert all `.ipynb` to `.py`

## 目標
把 TQuant-Lab 內所有 Jupyter notebook（`.ipynb`）轉成同名 `.py`，放在原檔旁邊，方便 grep、diff、IDE 編輯與 CI 跑語法檢查。輸出資料不嵌入，magics 註解掉以保持 `.py` 可被 import / py_compile。

## 計畫 milestone

- **M1** — 寫 stdlib-only 轉換器 `tools/ipynb_to_py.py`（無 nbformat 依賴，因系統 Python 受 PEP 668 鎖）
- **M2** — 對全 repo 跑一次，產生 77 個 `.py` 檔
- **M3** — Spot-check 4 個輸出檔的語法 + commit
- **M4** — 寫 `tools/check_converted_py.py` 並對全部 77 個輸出跑全量 py_compile + magic-leak 檢查
- **M5** — Pre-commit hook：當 `.ipynb` 被 stage 時自動重生對應 `.py` 並一起 commit
- **M6** — CI sync check：GitHub Actions 跑 `tools/check_ipynb_py_sync.py` + `tools/check_converted_py.py`，作為 pre-commit hook 的雙保險
- **M7** — `.gitattributes` 把 77 個生成 `.py` 標為 `linguist-generated=true`，讓 GitHub PR diff 收合 + 不計入語言統計

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

### M5 — Pre-commit hook 同步 `.ipynb` ↔ `.py`
- 在 `tools/ipynb_to_py.py` 新增 `--files <ipynb...>` 模式，允許 hook 對單一檔案而非整個 root 跑轉換；原 root walk 模式維持不變
- 寫了 `tools/hooks/pre-commit`：
  - 用 `git diff --cached --name-only --diff-filter=ACMR` 抓出本次要 commit 的 `.ipynb`（自動略過 deletion 與 `.ipynb_checkpoints/`）
  - 呼叫 `python3 tools/ipynb_to_py.py --files <staged>` 重生對應 `.py`
  - 對每個重生出來的 `.py` 跑 `git add`，讓它們一起進 commit
- 寫了 `tools/hooks/install.sh`：把 `tools/hooks/pre-commit` symlink 進 `.git/hooks/pre-commit`（idempotent，已存在的非 symlink hook 會 backup）
- 為什麼放 `tools/hooks/` 而不是直接寫 `.git/hooks/`：`.git/` 不會被 tracked，所以實際 hook 內容必須住在 repo 內、由使用者 opt-in 安裝
- End-to-end 測試（在 `Aroon.ipynb` 加 markdown cell → `git add` → 手動跑 hook）：
  - hook 偵測到 staged ipynb、轉換成功、`Aroon.py` sha 改變、被自動 stage
  - `git restore` 後 sha 還原 → 流程乾淨可逆

#### 安裝指令
```bash
tools/hooks/install.sh
# 之後 git commit 任何 .ipynb 變更時，對應的 .py 會被自動重生並 stage
```

#### 手動安裝（不想跑 install.sh）
```bash
ln -sf ../../tools/hooks/pre-commit .git/hooks/pre-commit
```

### M6 — CI sync check (GitHub Actions)
- Pre-commit hook 是 opt-in，使用者沒裝就會漏；CI 是強制守門員，補上這道
- 重構 `tools/ipynb_to_py.py`：把 `convert()` 拆成 `convert_to_str()`（純函式，回字串）+ `convert()`（呼叫前者寫檔）。對外行為不變；新增 import 點供 sync checker 復用同一份產生邏輯，避免轉換器與檢查器各自一份規則導致漂移
- 新增 `tools/check_ipynb_py_sync.py`：
  - 對每個 `.ipynb` 用 `convert_to_str()` 重產 expected text，與磁碟上 `.py` 做 byte-for-byte 比較
  - 不一致時印 unified diff（預設前 20 行，可 `--no-diff` 關閉）
  - Exit 0 = 全部同步；Exit 2 = 有 missing/drift；Exit 1 = usage error
  - 純 stdlib，CI 不需要 pip install
- 新增 `.github/workflows/ipynb-py-sync.yml`：
  - Trigger：`push` / `pull_request`，只在 `.ipynb` / `.py` / `tools/**` / 本 workflow 自己變動時跑
  - Steps：checkout → setup-python 3.11 → `check_ipynb_py_sync.py` → `check_converted_py.py`
  - 任一檢查失敗 CI 就紅，PR 無法合
- 本地驗證：
  - `python3 tools/check_ipynb_py_sync.py --quiet` → `In sync: 77/77`，exit 0
  - 故意 append 一行進 `Aroon.py` 模擬 drift → exit 2 + 報出 `DRIFT: Aroon.ipynb`，還原後 exit 0
  - Refactor 後 `python3 tools/ipynb_to_py.py --files Aroon.ipynb` + `check_converted_py.py` 仍全綠

#### 用法
```bash
# Local — 在 commit / push 前自己跑
python3 tools/check_ipynb_py_sync.py             # 預設掃當前目錄
python3 tools/check_ipynb_py_sync.py --quiet     # 只印 summary
python3 tools/check_ipynb_py_sync.py --no-diff   # 印 DRIFT 路徑但不印 diff 內文
python3 tools/check_ipynb_py_sync.py lecture     # 只掃子目錄
```

#### 失敗時怎麼修
```bash
python3 tools/ipynb_to_py.py .          # 重生全部 .py
git add '**/*.py'                       # 把更新後的 .py 一起 commit
```

### M7 — `.gitattributes` 標記生成檔
- 問題：77 個生成 `.py` 共 30,251 行，沒有特別標記的話 GitHub 會
  1. 在每個 notebook PR 把 diff 撐成兩倍（既看 `.ipynb` 又看 `.py`）
  2. 把這些「假 Python」算進 repo 的語言統計，蓋過真正的 tooling code
- 解法：新增 `.gitattributes` 用 inclusive default + 反向 override：
  ```
  *.py linguist-generated=true
  tools/**/*.py linguist-generated=false
  ```
  GitHub Linguist 規則：後寫的 pattern 覆蓋前面的，所以根目錄／`Problem/`／`example/`／`lecture/` 下的 `.py` 全部視為 generated；`tools/**/*.py`（3 個手寫工具）保留正常 diff 與語言統計
- 為什麼用「全部 generated + tools 例外」而非「明列 generated 目錄」：新增 notebook 不用改 `.gitattributes`，convention-over-configuration；缺點是若有人之後在 tools/ 以外手寫 `.py`，要記得加 override
- 本地驗證：
  ```bash
  git check-attr linguist-generated Aroon.py
  # → Aroon.py: linguist-generated: true

  git check-attr linguist-generated tools/ipynb_to_py.py
  # → tools/ipynb_to_py.py: linguist-generated: false
  ```
  跨中英檔名（含 `lecture/10分鐘體驗.py`、`example/TQ_期貨策略範例.py`）都正確解析
- 注意：`linguist-generated` 影響的是 GitHub UI；本地 `git diff`、`tools/check_ipynb_py_sync.py` 的 byte-for-byte 比對、CI sync check 全部維持不變
- 沒做的事（保留 reviewer 看 diff 的彈性）：
  - 沒設 `merge=ours`：notebook 兩支分支各自編輯時還是會正常衝突，不會被 silent overwrite
  - 沒設 `diff=python`：與 `linguist-generated=true` 會衝突，且 PR 用不到（GitHub 已收合）

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

若要解除 pre-commit hook：
```bash
rm .git/hooks/pre-commit
```

若要關掉 CI sync check：
```bash
rm .github/workflows/ipynb-py-sync.yml
# 或在 workflow 中加 `if: false` 暫停（commit 進去再 push）
```

若要讓 GitHub 重新把生成 `.py` 算進語言統計 / 展開 PR diff：
```bash
rm .gitattributes
# 或只刪掉 *.py 那兩行
```

## 已知限制 / 後續

- 沒處理 cell outputs（刻意丟掉，保持 .py 乾淨）
- magics 一律註解；若 `.py` 要直接執行（不是 import），自行把 `# !zipline ingest` 還原成 shell call
- Pre-commit hook 只看 staged 檔案；若 ipynb 被改但沒 `git add`，hook 不會跑（與 git 標準行為一致）
- Hook 是 opt-in（要跑 `tools/hooks/install.sh`）；M6 已補上 CI sync check 形成雙保險
- M6 的 workflow yaml 已 commit 進 repo，但要等到首次 `git push` 後 GitHub Actions 才會真正執行第一次（夜間 cron 不會 push）
- CI 採嚴格 byte-for-byte 比對；若日後改 `ipynb_to_py.py` 的 HEADER / CELL_SEP / sanitize 規則，要同步把全部 `.py` 重生並 commit，否則 CI 會紅
