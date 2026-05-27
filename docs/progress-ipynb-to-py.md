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
- **M8** — Unit tests `tools/tests/test_ipynb_to_py.py`：用 stdlib `unittest` 為 `_comment_block` / `_sanitize_code` / `convert_to_str` 補 edge case 覆蓋，並在 CI workflow 加上 `python3 -m unittest discover -s tools/tests`
- **M9** — Orphan `.py` detection：擴充 `tools/check_ipynb_py_sync.py` 加 `_orphan_py()`，掃出沒有對應 `.ipynb` 的孤兒 `.py`（notebook 被刪/改名但 `.py` 留下的狀況），補 9 個 unit test 進 `tools/tests/test_check_ipynb_py_sync.py`
- **M10** — Unit tests for `check_converted_py.py`：補 31 個 unit test 進 `tools/tests/test_check_converted_py.py`，覆蓋 `MAGIC_RE` / `_paired_py_files` / `_compile_check` / `_magic_check` / `main()` — 完成 toolchain 三支工具（converter / sync checker / converted-py validator）的測試三聯
- **M11** — Integration tests for `tools/hooks/pre-commit` + `tools/hooks/install.sh`：補 12 個 subprocess-based test 進 `tools/tests/test_pre_commit_hook.py`，每個 test 在自有 temp git repo 跑真實 hook（含 symlink install）。順手修掉一個被測試挖出來的 root-level `.ipynb_checkpoints/` filter bug
- **M12** — Pre-commit hook bidirectional sync：擴充 `tools/hooks/pre-commit` 在 `.ipynb` 被 delete / rename 時自動 `git rm` 掉對應的 `.py`，把 M11 文件裡的「known limitation: orphan after rename」直接關掉。翻轉 2 個鎖住舊行為的 hook test、補 1 個 deletion-without-existing-py silent test
- **M13** — Unit tests for `ipynb_to_py.main()` CLI entry point：補 12 個 test 進 `tools/tests/test_ipynb_to_py.py`，覆蓋 root-walk / `--files` / `--dry-run` / 錯誤路徑（empty tree / missing file / 非 .ipynb 副檔名 / mixed valid+invalid / malformed JSON），並小重構 `main()` 接受 `argv` 參數（對齊 M10 的 `check_converted_py.main(argv)` 與 M9 的 `check_ipynb_py_sync.main(argv)`）。完成四個 CLI 工具的 main() 級覆蓋。
- **M14** — Unit tests for `check_ipynb_py_sync.main()` + `_pairs` / `_diff_preview`：補 19 個 test 進 `tools/tests/test_check_ipynb_py_sync.py`。M9 只測了 `_orphan_py()`，sync checker 的 `main()`（in-sync / missing / drift / error / orphan 五條 exit path）與 `_pairs`（notebook discovery + checkpoint filter）、`_diff_preview`（drift 渲染 + truncation）一直沒有 unit 覆蓋。補完後 sync checker 與 converter（M13）、converted-py validator（M10）同樣達到 main() 級覆蓋，四支 CLI 工具的 entry point 全部上鎖。

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

### M8 — Unit tests for the converter
- 為什麼補：M1~M4 只用 77 個 notebook 做 smoke test，從沒驗證 edge case；之後若要動 `HEADER` / `CELL_SEP` / sanitize regex，沒有快速回饋
- 新增 `tools/tests/test_ipynb_to_py.py`（純 stdlib `unittest`，0 額外依賴），31 個 case 分三組：
  - **`_comment_block`** — 單行 / 多行 / 中夾空行 / 空字串 fallback 到 `#`
  - **`_sanitize_code`** — 純程式碼、`!` shell magic、`%` line magic、`%%` cell magic、`?prefix` / `suffix?` / `obj??`、縮排 magic、混合 magic + code
  - **`convert_to_str`** — 空 notebook、header 含 src 檔名、code/markdown/raw cell、空 source 跳過但保留 index、source 為 list of str、cell marker 含 kind+idx、未知 cell type fallback、cell 順序保留、缺 `cell_type` 預設 unknown、缺 `source` 跳過、idempotent
- **發現 + lock 進 test 的真實 quirk**：`_sanitize_code` 的 trailing newline 處理不對稱
  - input 沒 `\n` → output **有** `\n`
  - input 一個 `\n` → output **沒** `\n`（`splitlines()` 吃掉，`if not endswith('\n')` 分支不補）
  - 雙 `\n` → 一個 `\n`
  - 為什麼不修：77 個 generated `.py` 都依賴此行為通過 byte-for-byte CI；改 sanitize 規則會強制 regen 全部 77 檔 + diff 噪音
  - 補在 test 名稱 `test_trailing_newline_stripped_when_present` 內，附 docstring 解釋為何 lock 進 test
- 改 `.github/workflows/ipynb-py-sync.yml`：在 sync / compile check **之前**多一步 `python3 -m unittest discover -s tools/tests -v`；轉換器壞了會在最便宜的層級先紅
- 不需要 `__init__.py`：unittest discover 從 3.3 開始支援 namespace package；`__pycache__/` 已在 `.gitignore`
- 本地驗證：
  - `python3 tools/tests/test_ipynb_to_py.py -v` → `Ran 31 tests in 0.007s OK`
  - `python3 -m unittest discover -s tools/tests -v` → 同樣 31 OK
  - `python3 tools/check_ipynb_py_sync.py --quiet` → 仍 77/77
  - `python3 tools/check_converted_py.py --quiet` → 仍 77/77

#### 用法
```bash
# 跑全部 unit test
python3 tools/tests/test_ipynb_to_py.py
python3 tools/tests/test_ipynb_to_py.py -v        # verbose
python3 -m unittest discover -s tools/tests       # discover mode（CI 用這個）

# 跑單一 test class
python3 -m unittest tools.tests.test_ipynb_to_py.SanitizeCodeTests
```

### M9 — Orphan `.py` detection
- 為什麼補：M6 的 `check_ipynb_py_sync.py` 只 walk `.ipynb`，所以「`.ipynb` 被刪除/改名、但 `.py` 留下」這種 stale orphan 完全偵測不到 — sync check 不會看見、`check_converted_py.py` 也只從 ipynb 端 iterate。CI 與 pre-commit hook 都有這個盲點
- 解法：在 `check_ipynb_py_sync.py` 加 `_orphan_py(root)` helper：
  - `rglob('*.py')` 找全部 `.py`
  - 排除 skip dirs：`.git` / `.github` / `.ipynb_checkpoints` / `__pycache__` / `.venv` / `venv`
  - 排除 handwritten 區（`tools/` 之下）：與 M7 的 `.gitattributes` 規則 (`tools/**/*.py linguist-generated=false`) 對齊
  - 若 `.py` 旁邊沒有同名 `.ipynb` 就視為 orphan
  - 回傳 root-relative `Path` list，並依 pathlib `_parts` tuple 排序（同 prefix 時 directory 內容先於同層檔案，例如 `a/c.py` < `a.py`）
- `main()` 整合：
  - `bad = missing + drift + errors + orphans`（用 union 算總壞數，避免 orphan 重複計入 in-sync）
  - Summary 多印一行 `Orphan .py (no .ipynb): N`
  - non-quiet 模式對每筆印 `ORPHAN: <path> (no matching .ipynb — delete it or restore the notebook)`
  - 退出時若有 orphan 額外印「delete the stale .py or restore the missing .ipynb」提示
  - Exit code 仍是 2（與 missing/drift 同等對待）
- Smoke test（手動，無汙染 repo）：
  - Clean: `check_ipynb_py_sync.py --quiet` → `In sync: 77/77`、`Orphan .py: 0`、exit 0
  - Inject `example/stale_orphan.py` → exit 2，列出 `ORPHAN: example/stale_orphan.py`
  - 刪除後再跑 → exit 0、orphan count 0
- Unit test `tools/tests/test_check_ipynb_py_sync.py`（純 stdlib `unittest`，9 cases，全部用 `tempfile.TemporaryDirectory()` 隔離）：
  - 空目錄 → 0 orphan
  - 配對 `.ipynb`+`.py` → 0 orphan
  - 純 `.py`（root 與子目錄各一）→ 各自被偵測
  - `tools/` 下任何 `.py`（含 `tools/tests/`、`tools/hooks/`）→ 永遠不視為 orphan
  - 全部 skip dir（`.git` / `.github` / `.ipynb_checkpoints` / `__pycache__` / `.venv` / `venv`） → 永遠不視為 orphan
  - 排序順序 lock 進 test（含 docstring 說明 pathlib parts-tuple 排序行為）
  - 混合 tree（兩配對 + 一 orphan + 一 handwritten） → 只回那一個 orphan
  - 「`.ipynb` 沒有對應 `.py`」（missing）→ 不算 orphan（由 main loop 另外回報），明確區分職責
- CI workflow 無需改動：`.github/workflows/ipynb-py-sync.yml` 已經跑 `python3 -m unittest discover -s tools/tests`，新 test 自動被 pick up；且 sync step 已經跑 `check_ipynb_py_sync.py`，orphan 行為自動接上
- 本地驗證：
  - `python3 tools/tests/test_check_ipynb_py_sync.py` → `Ran 9 tests OK`
  - `python3 -m unittest discover -s tools/tests` → `Ran 40 tests OK`（M8 31 + M9 9）
  - `python3 tools/check_ipynb_py_sync.py --quiet` → 77/77 in sync，0 orphan，exit 0
  - `python3 tools/check_converted_py.py --quiet` → 77/77 OK，exit 0

#### 用法
```bash
# Orphan 偵測現在內建在 sync check 裡，不用獨立指令
python3 tools/check_ipynb_py_sync.py             # 含 orphan 偵測
python3 tools/check_ipynb_py_sync.py --quiet     # 只看 summary 行的 "Orphan .py: N"
```

#### 失敗時怎麼修
```bash
# Orphan 出現代表 .ipynb 不存在了。兩個選項：
# 1. 確實要刪這個 notebook → 刪掉 .py
git rm example/stale_orphan.py

# 2. notebook 被誤刪 → 從歷史救回
git checkout HEAD~1 -- example/SomeNotebook.ipynb
python3 tools/ipynb_to_py.py --files example/SomeNotebook.ipynb
```

### M10 — Unit tests for `check_converted_py.py`
- 為什麼補：toolchain 三支工具中，`check_converted_py.py`（py_compile + magic-leak validator）是 M8（converter）與 M9（sync checker）之後唯一還沒有 unit test 的。CI 對全 77 個 notebook 做 smoke test 雖然能擋大規模回歸，但 helper 級別的行為改動沒有快速回饋；未來若改 `MAGIC_RE` 規則或 truncate 長度，沒有 unit test 容易整批失靈
- 新增 `tools/tests/test_check_converted_py.py`（純 stdlib `unittest`，0 額外依賴），31 個 case 分五組：
  - **`MagicRegexTests`（6 cases）** — pin `MAGIC_RE` 接受 `!` / `%` / `%%` / `?` 且拒絕 `# !` / 純程式碼 / 空字串
  - **`PairedPyFilesTests`（7 cases）** — 空 tree、root 單檔、子目錄、`.ipynb_checkpoints` 過濾（含 nested）、`.py` 不存在仍配對、多檔 walk
  - **`CompileCheckTests`（6 cases）** — 合法檔回 None、空檔回 None、純註解回 None、syntax error 回字串、`!ls` / `%matplotlib` 因 syntax error 被擋
  - **`MagicCheckTests`（6 cases）** — 乾淨檔回 []、`# !ls` 不誤判、leaked bang 含 line number、`%` 與 `?` 同檔多行、`lstrip()` 後 indent magic 也被抓、長 line 截到 120 chars
  - **`MainTests`（6 cases）** — 空 root rc=1、全 pass rc=0、missing/compile/magic 任一觸發 rc=2、`--quiet` 抑制 per-file 行
- 整合 `_run()` helper 用 `redirect_stdout` / `redirect_stderr` 捕獲輸出，免污染 test runner
- 不需動 CI workflow：`.github/workflows/ipynb-py-sync.yml` 已經跑 `python3 -m unittest discover -s tools/tests`，新 test 自動被 pick up
- 本地驗證：
  - `python3 tools/tests/test_check_converted_py.py -v` → `Ran 31 tests OK`
  - `python3 -m unittest discover -s tools/tests` → `Ran 71 tests OK`（M8 31 + M9 9 + M10 31）
  - `python3 tools/check_ipynb_py_sync.py --quiet` → 77/77 in sync、0 orphan、exit 0
  - `python3 tools/check_converted_py.py --quiet` → 77/77 OK、exit 0

#### 用法
```bash
# 跑 M10 的 31 個 test
python3 tools/tests/test_check_converted_py.py
python3 tools/tests/test_check_converted_py.py -v

# 跑單一 test class
python3 -m unittest tools.tests.test_check_converted_py.MagicCheckTests
python3 -m unittest tools.tests.test_check_converted_py.MainTests
```

### M11 — Integration tests for the pre-commit hook
- 為什麼補：toolchain 四個元件中（converter / sync checker / converted-py validator / pre-commit hook），前三個在 M8/M9/M10 都有 unit test，只剩 bash 寫的 `tools/hooks/pre-commit` + `tools/hooks/install.sh` 完全沒測過。M5 結尾只有手動跑 `Aroon.ipynb` 的 end-to-end smoke。未來要動 hook 的 filter / `set -euo pipefail` / `--diff-filter` flags，沒有快速回饋
- 新增 `tools/tests/test_pre_commit_hook.py`（純 stdlib `unittest` + `subprocess` + `tempfile`，0 額外依賴），12 個 case 分兩組：
  - **`HookBehaviourTests`（9 cases）** — 每個 test 在自有 temp git repo 跑：
    - 把 `tools/hooks/pre-commit`、`tools/hooks/install.sh`、`tools/ipynb_to_py.py` 複製進 temp repo
    - 用 `os.symlink('../../tools/hooks/pre-commit', '.git/hooks/pre-commit')` 安裝（與 `install.sh` 同一形式）
    - 透過 `subprocess.run(['git', 'commit', ...])` 觸發 hook，再驗證 `.py` 是否被產生 + 進 commit
    - 涵蓋：無 ipynb staged（passthrough）/ 新增 ipynb / 修改 ipynb / 刪除 ipynb（不該觸發）/ `.ipynb_checkpoints/` 被過濾 / 多檔批次 / `git mv` rename / rename 留下 orphan `.py`（已知限制 lock 進 test）/ HEADER + cell marker end-to-end
  - **`InstallShTests`（3 cases）** — 直接跑 `./tools/hooks/install.sh`：
    - Fresh install → `.git/hooks/pre-commit` 是 symlink、target 為相對路徑 `../../tools/hooks/pre-commit`
    - 重跑 idempotent → 無 backup 檔產生
    - Pre-existing 非 symlink hook → 備份到 `pre-commit.backup.<epoch>` 後安裝 symlink
- **測試挖到的真實 bug + 順手修掉**：原 hook filter `grep -v '/\.ipynb_checkpoints/'` 要求 `.ipynb_checkpoints/` 在子目錄裡才會被過濾；root-level（例如 Jupyter 在 repo 根目錄開 `Aroon.ipynb` 後產生的 `.ipynb_checkpoints/Aroon-checkpoint.ipynb`）會繞過 filter。改成 `grep -vE '(^|/)\.ipynb_checkpoints/'` 同時匹配兩種；`.ipynb_checkpoints/` 本來就在 `.gitignore` 內，這是 defense-in-depth 不是 hot path
- 為什麼用 subprocess 而非 mock：hook 是 bash 腳本，內部呼叫 `git diff` / `mapfile` / `python3` 多支真實工具；mock 任何一支都會讓 test 變得「測 mock 而不是測 hook」。每個 test 用 `tempfile.TemporaryDirectory()` 起新 git repo，慢一點（12 個 test 跑 0.5s）但對 hook 的真實行為有 byte-for-byte 保證
- 不需動 CI workflow：`.github/workflows/ipynb-py-sync.yml` 已經跑 `python3 -m unittest discover -s tools/tests`，新 test 自動 pick up
- 本地驗證：
  - `python3 tools/tests/test_pre_commit_hook.py -v` → `Ran 12 tests OK`
  - `python3 -m unittest discover -s tools/tests` → `Ran 83 tests OK`（M8 31 + M9 9 + M10 31 + M11 12）
  - `python3 tools/check_ipynb_py_sync.py --quiet` → 77/77 in sync、0 orphan、exit 0
  - `python3 tools/check_converted_py.py --quiet` → 77/77 OK、exit 0

#### 用法
```bash
# 跑 M11 的 12 個 hook 測試
python3 tools/tests/test_pre_commit_hook.py
python3 tools/tests/test_pre_commit_hook.py -v

# 跑單一 test class
python3 -m unittest tools.tests.test_pre_commit_hook.HookBehaviourTests
python3 -m unittest tools.tests.test_pre_commit_hook.InstallShTests
```

### M12 — Hook 在 delete / rename 時自動清掉孤兒 `.py`
- 為什麼補：M11 的進度文末明確列了「`git mv old.ipynb new.ipynb` 之後 hook 不會刪 `old.py`，靠 M9 的 `_orphan_py()` 下游抓」這條已知限制。雖然 sync check 能在 CI 抓到，但需要使用者額外再跑一次 `python3 tools/check_ipynb_py_sync.py` 或等 CI 紅；hook 自己 close 這個 loop 比較對稱
- 改 `tools/hooks/pre-commit`：
  - 在原本 `--diff-filter=ACMR` 的 staged 清單之外，多收一份 `--no-renames --diff-filter=D` 的 removed 清單
  - `--no-renames` 強制 git 把 rename 拆成 D-old + A-new，所以 rename target 走 ACMR 路徑（→ 重生 new.py），rename source 走 D 路徑（→ 刪掉 old.py）；deletion 也走同一條 D 路徑
  - 對 removed 清單裡每個 `<nb>.ipynb`，跑 `git rm -f --ignore-unmatch --quiet -- "${nb%.ipynb}.py"`；`--ignore-unmatch` 讓「`.ipynb` 從未產生 `.py`」這種情境靜默不噴錯
  - 為什麼用 `git rm` 而非 `rm -- $py && git add -u`：`git rm` 同時處理 index + working tree，且對「.py 沒被 tracked」的情況 `--ignore-unmatch` 是官方支援的旁路
- 改 `tools/tests/test_pre_commit_hook.py`：
  - 翻轉 `test_deleted_ipynb_does_not_invoke_converter` → 新名 `test_deleted_ipynb_also_removes_py_sibling`，驗證使用者只 stage `.ipynb` 刪除時 `.py` 也跟著消失（hook 自己處理）
  - 翻轉 `test_rename_does_not_clean_up_old_py` → 新名 `test_rename_cleans_up_old_py`，驗證 `git mv old.ipynb new.ipynb` 後 `old.py` 不存在、`new.py` 自動生成
  - 補新 case `test_deleted_ipynb_without_existing_py_is_silent`：先 `git rm orphan.py` 把 `.py` 拿掉再 commit `.ipynb` 刪除，確認 hook 在沒有 sibling 可刪時不噴 error code（`--ignore-unmatch` 的保險）
- 沒動的東西：converter / sync checker / `_orphan_py()` 全部沒改。`_orphan_py()` 仍是 CI 端的雙保險，捕捉「使用者沒裝 hook 也沒清 .py」的情境
- 為什麼這條限制這次值得處理：M11 列為「known limitation」+「locked into test」就是技術債的訊號；現在三個 toolchain 元件對 rename 的處理是非對稱的（converter 處理 staged ACMR、sync checker 報 orphan、hook 只前向），統一成 hook 雙向後行為更可預期
- 本地驗證：
  - `python3 tools/tests/test_pre_commit_hook.py -v` → `Ran 13 tests OK`
  - `python3 -m unittest discover -s tools/tests` → `Ran 84 tests OK`（M8 31 + M9 9 + M10 31 + M11→M12 13）
  - `python3 tools/check_ipynb_py_sync.py --quiet` → 77/77 in sync、0 orphan、exit 0
  - `python3 tools/check_converted_py.py --quiet` → 77/77 OK、exit 0

#### 用法
- 安裝後一切照舊：`tools/hooks/install.sh` 不用重跑（symlink 內容沒變）。下次 commit 時若有 `.ipynb` 被刪 / rename，hook 會多印一行
  ```
  [ipynb->py hook] removing .py sibling for N deleted/renamed notebook(s)...
  ```
- 想看 hook 真實行為差異：在 dev branch 跑
  ```bash
  git mv example/SomeNotebook.ipynb example/SomeNotebook_v2.ipynb
  git commit -m 'rename'
  # → 應該看到 .py sibling 也被改名、不留 orphan
  python3 tools/check_ipynb_py_sync.py --quiet  # 應顯示 0 orphan
  ```

### M13 — Unit tests for `ipynb_to_py.main()` CLI entry point
- 為什麼補：M8/M9/M10 都把對應工具的 `main()` 行為 lock 進 test，唯獨 M8 漏掉了 `ipynb_to_py.py` 自己的 `main()`。converter 是整條 toolchain 的源頭，CLI 行為（root-walk vs `--files` vs `--dry-run` vs 各種 error path）若回歸，下游所有檢查與 hook 都會跟著炸。這個缺口比想像中明顯，且補完後四支工具（converter / sync checker / converted-py validator / pre-commit hook）main() 級覆蓋一致。
- 小重構 `tools/ipynb_to_py.py`：`main()` 簽名從 `main() -> int` 改成 `main(argv: list[str] | None = None) -> int`，`ap.parse_args()` → `ap.parse_args(argv)`。argparse 對 `parse_args(None)` 預設取 `sys.argv[1:]`，所以 CLI 對外行為零變化；唯一目的是讓 unit test 可以直接傳 `argv` list 而不用 monkey-patch `sys.argv`。同時跟 M9 的 `check_ipynb_py_sync.main(argv)` 與 M10 的 `check_converted_py.main(argv)` 對齊。
- 在 `tools/tests/test_ipynb_to_py.py` 新增 `MainTests` class，12 個 case 用 `tempfile.TemporaryDirectory()` + `os.chdir()` 隔離（避免汙染 cwd），透過 `redirect_stdout` / `redirect_stderr` 捕獲輸出：
  - **Root-walk 模式（4 cases）** — 空 root → rc=1 + stderr `No .ipynb under`；nested notebooks 都轉成功 + summary 正確；root-level `.ipynb_checkpoints/` 完全跳過；nested `.ipynb_checkpoints/` 跳過但旁邊真 notebook 仍轉
  - **--files 模式（5 cases）** — 單檔成功；多檔成功；不存在的 path → rc=1 + ERR；非 `.ipynb` 副檔名 → rc=1 + ERR；mixed valid+invalid → rc=1 且**所有**檔案都不轉（atomic-ish guard，由 main 先驗證再 convert）
  - **--dry-run（2 cases）** — root-walk 與 --files 都不寫檔；stdout 有 `[dry]` 標記與 `Converted 0/N notebooks.` summary
  - **Malformed JSON（1 case）** — `Bad.ipynb` 是壞 JSON、`Good.ipynb` 正常：rc=0、stderr 報 `ERR Bad.ipynb`、`Good.py` 仍生成、stdout `Converted 1/2`。Lock 進 test 的行為：per-file `try/except` 寬鬆 — 一個壞 notebook 不會中斷整個 batch
- 不需動 CI workflow：`.github/workflows/ipynb-py-sync.yml` 已經跑 `python3 -m unittest discover -s tools/tests`，12 個新 test 自動 pick up
- 本地驗證：
  - `python3 tools/tests/test_ipynb_to_py.py -v` → `Ran 43 tests OK`（原 31 + M13 12）
  - `python3 -m unittest discover -s tools/tests` → `Ran 96 tests OK`（M8 31+12 + M9 9 + M10 31 + M11→M12 13）
  - `python3 tools/check_ipynb_py_sync.py --quiet` → 77/77 in sync、0 orphan、exit 0
  - `python3 tools/check_converted_py.py --quiet` → 77/77 OK、exit 0

#### 用法
```bash
# 只跑 M13 新增的 MainTests class
python3 -m unittest tools.tests.test_ipynb_to_py.MainTests
python3 -m unittest tools.tests.test_ipynb_to_py.MainTests -v
```

#### 副作用 / 注意
- `MainTests.setUp` 會 `os.chdir(temp_root)` 並在 `tearDown` 還原；若日後改成平行 test runner（unittest 預設 sequential 不受影響），需要把 chdir 改成 `subprocess` 隔離
- `test_malformed_notebook_reported_but_does_not_abort` 把「main() 對壞 ipynb 寬鬆」這個行為 lock 進來；若日後想改成 strict（壞檔讓整個 batch 失敗 + rc=1），要同步翻轉這個 test 並加 `--strict` flag

### M14 — Unit tests for `check_ipynb_py_sync.main()` + `_pairs` / `_diff_preview`
- 為什麼補：四支 CLI 工具裡，converter（M13 `MainTests`）與 converted-py validator（M10 `MainTests`）都已把 `main()` 行為 lock 進 test，連 sync checker 的 `_orphan_py()` helper 也在 M9 補過；唯獨 sync checker 自己的 `main()` 從沒被 unit 測過。`test_check_ipynb_py_sync.py` 的舊 docstring 甚至直接寫明「in-sync / drift / missing paths 只靠 CI 對真實 77 對 notebook 做 end-to-end」——這正是技術債訊號：helper 級重構（改 summary 措辭、改 diff truncation 長度、改 exit code 對應）沒有快速回饋。M14 把這條補上，sync checker 達到與其餘三支工具一致的 main() 級覆蓋
- 在 `tools/tests/test_check_ipynb_py_sync.py` 新增 3 個 test class，19 個 case（原 9 個 `OrphanPyTests` 全部保留，檔案總計 28 個 test）：
  - **`PairsTests`（7 cases）** — 空 tree → []；root 單檔配對 `.py` suffix；nested notebook 配對；root-level `.ipynb_checkpoints/` 過濾；nested `.ipynb_checkpoints/` 過濾；`.py` 不存在仍配對（missing 由 main 另報）；多檔 `sorted()` 順序
  - **`DiffPreviewTests`（4 cases）** — 相同輸入 → 空字串（`difflib` 無差異）；有差異時 from/to label（`(on disk)` / `(expected from .ipynb)`）都在；`+expected` / `-actual` 標記都在；超過 `max_lines` 時出現 `more diff lines truncated` 且總行數被截到 ≤ max_lines+1
  - **`MainTests`（8 cases）** — 空 tree → rc=1 + stderr `No .ipynb files`；全 in-sync → rc=0 + `In sync: 2`；missing `.py` → rc=2 + `MISSING:`；drift → rc=2 + `DRIFT:` + diff body（含 `(on disk)`）；`--no-diff` drift → rc=2 + `DRIFT:` 但**無** diff body；orphan `.py` → rc=2 + `ORPHAN:`；malformed `.ipynb` + 既有 `.py` → 走 `convert_to_str` 例外路徑 → rc=2 + `ERROR:`；`--quiet` 抑制 per-file 行但保留 summary 計數
- 設計細節：
  - 新增 `_synced_pair(path)` helper — 用 `convert_to_str(nb)` 寫出 byte-for-byte 相符的 `.py`，這樣 in-sync 測試不會因 converter 規則微調而假性 drift（測試與真實轉換邏輯同源，避免硬編 expected 字串）
  - summary 計數斷言全用 `assertRegex(stdout, r'In sync:\s+2')` 這類 **regex + `\s+`**，刻意不硬編空白數 — 與 M10 `MainTests` 硬編 `'OK:                  2'` 不同，對日後調整欄位對齊較不脆弱（見「已知限制」對照）
  - drift 測試靠「先 `_synced_pair` 再 append 一行」製造，最小化噪音；`--no-diff` 用「`(on disk)` 不在 stdout」反向驗證 diff body 被抑制
  - `_run(*argv)` helper 沿用 M10/M13 的 `redirect_stdout` / `redirect_stderr` + `io.StringIO()` 模式捕獲輸出，免污染 test runner；**不需** `os.chdir()`（main 接受 root 位置參數，直接傳 temp dir）所以沒有 M13 的 cwd 隔離副作用
- 不需動 production code：`check_ipynb_py_sync.py` 完全沒改（M9 已把 `main(argv)` 簽名就緒）。純測試新增
- 不需動 CI workflow：`.github/workflows/ipynb-py-sync.yml` 已跑 `python3 -m unittest discover -s tools/tests`，19 個新 test 自動 pick up
- 本地驗證：
  - `python3 tools/tests/test_check_ipynb_py_sync.py -v` → `Ran 28 tests OK`（原 9 + M14 19）
  - `python3 -m unittest discover -s tools/tests` → `Ran 115 tests OK`（M8 31+12 + M9 9+19 + M10 31 + M11→M12 13）
  - `python3 tools/check_ipynb_py_sync.py --quiet` → 77/77 in sync、0 orphan、exit 0
  - `python3 tools/check_converted_py.py --quiet` → 77/77 OK、exit 0

#### 用法
```bash
# 只跑 M14 新增的 class
python3 -m unittest tools.tests.test_check_ipynb_py_sync.PairsTests
python3 -m unittest tools.tests.test_check_ipynb_py_sync.DiffPreviewTests
python3 -m unittest tools.tests.test_check_ipynb_py_sync.MainTests -v
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

若要拔掉 unit tests：
```bash
rm -r tools/tests
# 並把 .github/workflows/ipynb-py-sync.yml 的 "Run unit tests" step 刪掉
```

若要關掉 orphan `.py` 偵測：
```bash
# 還原 tools/check_ipynb_py_sync.py 到 M8 版本
git revert <M9-commit-sha>
# 或手動拔掉 _orphan_py() / summary 中 "Orphan .py" 那行
```

若要拔掉 hook integration test：
```bash
rm tools/tests/test_pre_commit_hook.py
# CI workflow 不需動（discover 模式自動少抓 13 個 test）
```

若要還原 M12 的 hook 雙向同步（讓 hook 只前向、rename / delete 後 .py 變 orphan）：
```bash
# 拔掉 hook 裡的 removed 區塊與 git rm 迴圈
git revert <M12-commit-sha>
# 同步把 hook test 兩個被翻轉的 case 改回（test_deleted_ipynb_does_not_invoke_converter / test_rename_does_not_clean_up_old_py）
```

若要還原 M13 的 `main(argv)` 簽名與 MainTests：
```bash
# 把 ipynb_to_py.main 改回 main() -> int + ap.parse_args() 即可（CLI 對外行為原本就一樣）
# 並從 test_ipynb_to_py.py 拔掉 MainTests class（其餘 31 個 helper test 不受影響）
git revert <M13-commit-sha>
```

若要拔掉 M14 的 sync-checker main() 測試：
```bash
# 只刪 M14 新增的三個 class，保留 M9 的 OrphanPyTests
git revert <M14-commit-sha>
# 或手動從 test_check_ipynb_py_sync.py 移除 PairsTests / DiffPreviewTests / MainTests
# （check_ipynb_py_sync.py production code 沒改，無需動）
```

## 已知限制 / 後續

- 沒處理 cell outputs（刻意丟掉，保持 .py 乾淨）
- magics 一律註解；若 `.py` 要直接執行（不是 import），自行把 `# !zipline ingest` 還原成 shell call
- Pre-commit hook 只看 staged 檔案；若 ipynb 被改但沒 `git add`，hook 不會跑（與 git 標準行為一致）
- Hook 是 opt-in（要跑 `tools/hooks/install.sh`）；M6 已補上 CI sync check 形成雙保險
- M6 的 workflow yaml 已 commit 進 repo，但要等到首次 `git push` 後 GitHub Actions 才會真正執行第一次（夜間 cron 不會 push）
- CI 採嚴格 byte-for-byte 比對；若日後改 `ipynb_to_py.py` 的 HEADER / CELL_SEP / sanitize 規則，要同步把全部 `.py` 重生並 commit，否則 CI 會紅
- `_sanitize_code` 的 trailing-newline 不對稱已 lock 進 M8 的 unit test（見 `test_trailing_newline_stripped_when_present`）。若要把它「修正」成 always-trailing-newline，必須同時 regen 全部 77 個 `.py` 並更新 test 預期
- M9 的 orphan 偵測 hard-codes 兩組目錄常量（`_SKIP_DIR_PARTS` / `_HANDWRITTEN_DIR_PARTS`）。若日後在 `tools/` 以外另起手寫 Python 模組（例如 `scripts/` 或 `src/`），要記得加進 `_HANDWRITTEN_DIR_PARTS`，否則會被誤判為 orphan
- M10 的 `MainTests` 直接依賴 `main()` 內 summary 字串格式（`'OK:                  2'` / `'Missing .py sibling: 1'`）。若改 print 對齊空白數或欄位措辭，會同時打到這幾個 test，記得一起更新
- M11 的 hook test 用真實 `git commit` 驅動 subprocess，所以對 git CLI 行為有依賴（特別是 `git diff --cached --name-only --diff-filter=ACMR -z` 對 rename 的處理）。若日後升級 git 主版本（不太可能改這個 contract），rename 測試可能要重看
- ~~M11 已知 lock 進 test 的限制：hook 在 `git mv old.ipynb new.ipynb` 後不會刪除 `old.py`（單向同步）~~ — **M12 已關掉**：hook 現在同時收 ACMR（regenerate）與 `--no-renames -D`（remove），rename / delete 都會清掉 sibling `.py`。M9 的 `_orphan_py()` 仍作為 CI 端 fallback，捕捉「沒裝 hook」的情境
- M11 修掉的小 bug：`tools/hooks/pre-commit` 的 `.ipynb_checkpoints/` filter 原本沒匹配 root-level（例如 `.ipynb_checkpoints/Aroon-checkpoint.ipynb`），已改為 `(^|/)\.ipynb_checkpoints/`。實務上這個目錄已在 `.gitignore`，所以是 defense-in-depth
- M13 的 `MainTests` 用 `os.chdir(temp_root)` 隔離 cwd。若日後 CI 改用平行 test runner（如 pytest-xdist），這些 test 會互踩 — 要重寫成 subprocess 隔離或加 `setUpClass` 級鎖
- M13 把「main() 對單一 malformed `.ipynb` 寬鬆繼續」的行為 lock 進 `test_malformed_notebook_reported_but_does_not_abort`。若日後想改成「壞檔即整批失敗 + rc=1」，要同步翻轉這個 test 並加 `--strict` flag
- M14 的 `MainTests` 刻意用 `assertRegex(..., r'In sync:\s+2')` 而非硬編空白數，所以調 summary 欄位對齊不會打到它；但仍依賴 label 文字（`In sync:` / `Missing .py sibling:` / `Conversion errors:` / `Orphan .py (no .ipynb):`）與 per-file 前綴（`MISSING:` / `DRIFT:` / `ERROR:` / `ORPHAN:`）。若改這些措辭，要一起更新。另外 `test_drift_no_diff_suppresses_diff_body` 用「`(on disk)` 字串是否出現」當作 diff body 的 proxy，若把 `_diff_preview` 的 fromfile label 改掉，這條 assertion 要跟著改
