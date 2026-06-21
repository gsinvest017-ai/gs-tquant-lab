# `tools/` — `.ipynb` → `.py` toolchain

把 TQuant-Lab 內所有 Jupyter notebook（`.ipynb`）轉成同名 `.py` 放在原檔旁邊，
方便 grep / diff / IDE 編輯與 CI 語法檢查。輸出資料不嵌入、IPython magics 註解掉，
讓每個 `.py` 都能 `py_compile`。

> 這份是 toolchain 的**參考文件（reference）**；逐個 milestone 的決策過程與歷史
> 記在 [`../docs/progress-ipynb-to-py.md`](../docs/progress-ipynb-to-py.md)。

全部工具皆 **stdlib-only**（系統 Python 受 PEP 668 鎖，無法 `pip install`；
不依賴 nbformat / jupytext / PyYAML）。

## Tools

| Tool | 角色 | 一句話 |
|------|------|--------|
| `tools/ipynb_to_py.py` | converter（轉換器） | 逐 cell 把 `.ipynb` 轉出同名 `.py`；magics 註解化、markdown 變 `#` 註解 |
| `tools/check_ipynb_py_sync.py` | sync checker（同步檢查） | 用 converter 重產 expected text 與磁碟上 `.py` byte-for-byte 比對；另偵測 orphan `.py` |
| `tools/check_converted_py.py` | converted-py validator（產物驗證） | 對每個生成 `.py` 跑 `py_compile` + magic-leak 掃描 |
| `tools/check_all.py` | aggregate runner（本地一鍵） | step-for-step 對齊 CI workflow，一條指令重現 CI 把關 |
| `tools/hooks/pre-commit` | git hook | stage `.ipynb` 時自動重生 `.py` 一起 commit；delete / rename 時自動 `git rm` 孤兒 `.py` |
| `tools/hooks/pre-push` | git hook | push 前跑 `check_all.py --skip-tests`（CI step 2-4），artifacts 不同步就擋下 push |
| `tools/hooks/install.sh` | hook installer | 把 `pre-commit` / `pre-push` symlink 進 `.git/hooks/`（idempotent，會 backup 既有 hook） |

## 常用指令

```bash
# 全 repo 轉檔（重生所有 .py）
python3 tools/ipynb_to_py.py .

# 單檔轉換（hook 內部用的模式）
python3 tools/ipynb_to_py.py --files Aroon.ipynb example/foo.ipynb

# CI 想擋壞 notebook：strict 模式（任一轉換失敗回 rc=1，仍 try-all）
python3 tools/ipynb_to_py.py --strict .

# 零副作用預掃（parse 但不寫檔）——CI 最便宜的 fail-fast gate
python3 tools/ipynb_to_py.py --strict --dry-run .

# 同步檢查（含 orphan 偵測）
python3 tools/check_ipynb_py_sync.py            # 預設掃當前目錄
python3 tools/check_ipynb_py_sync.py --quiet    # 只印 summary
python3 tools/check_ipynb_py_sync.py --no-diff  # 印 DRIFT 路徑但不印 diff 內文

# 產物驗證（py_compile + magic-leak）
python3 tools/check_converted_py.py
python3 tools/check_converted_py.py --quiet

# 一鍵跑完整套（== CI），全跑不 fail-fast、一次列出所有問題
python3 tools/check_all.py
python3 tools/check_all.py --quiet        # checker 只印 summary
python3 tools/check_all.py --skip-tests   # 略過 unittest step（快速 wiring 檢查）
```

## 安裝 git hooks

```bash
tools/hooks/install.sh
# 一次裝兩個 hook：
#   pre-commit — commit 任何 .ipynb 變更時自動重生 / 同步對應的 .py；
#                .ipynb 被刪 / rename 時對應的 .py 也會被自動 git rm。
#   pre-push   — push 前跑 check_all.py --skip-tests（CI step 2-4），
#                .py 與 .ipynb 不同步 / 無法 compile 就擋下 push。
```

手動安裝（不想跑 install.sh）：

```bash
ln -sf ../../tools/hooks/pre-commit .git/hooks/pre-commit
ln -sf ../../tools/hooks/pre-push   .git/hooks/pre-push
```

> `pre-push` 刻意只跑 `--skip-tests`（CI step 2-4 的 artifact 檢查），不跑
> unittest step（CI step 1）：單元測試驗的是 toolchain 本身、不是你要 push 的
> notebook，CI 仍會跑。要跳過 hook：`git push --no-verify`。

## CI 對應

`.github/workflows/ipynb-py-sync.yml` 在 push / PR 觸碰 `.ipynb` / `.py` / `tools/**`
時跑，步驟與 `check_all.py` **step-for-step 對齊**（由 `WorkflowParityTests` 鎖死）：

1. `python3 -m unittest discover -s tools/tests` — 單元測試
2. `python3 tools/ipynb_to_py.py --strict --dry-run .` — strict pre-scan gate
3. `python3 tools/check_ipynb_py_sync.py .` — 同步 + orphan 檢查
4. `python3 tools/check_converted_py.py .` — 產物驗證

任一步失敗 CI 就紅、PR 無法合。`python3 tools/check_all.py` 在本地重現這四步，
所以綠的本地 run 可預測綠的 CI run。

## 測試

```bash
# 全部單元 / 整合測試（CI 用 discover 模式）
python3 -m unittest discover -s tools/tests

# 單一檔 / 單一 class
python3 tools/tests/test_check_all.py -v
python3 -m unittest tools.tests.test_check_all.WorkflowParityTests
```

| Test 檔 | 覆蓋對象 |
|---------|----------|
| `tools/tests/test_ipynb_to_py.py` | converter helper + `main()` CLI（含 `--strict` / `--dry-run`） |
| `tools/tests/test_check_ipynb_py_sync.py` | sync checker `main()` / `_pairs` / `_diff_preview` / `_orphan_py` + `.gitattributes` parity |
| `tools/tests/test_check_converted_py.py` | validator 共用的 `_is_magic_line` predicate / `_paired_py_files` / `_compile_check` / `_magic_check` / `main()` |
| `tools/tests/test_pre_commit_hook.py` | hooks（pre-commit / pre-push）+ `install.sh`（每 test 起自有 temp git repo 跑真實 hook） |
| `tools/tests/test_check_all.py` | aggregate runner + CI workflow parity guard |
| `tools/tests/test_readme.py` | 本 README 的 tool 清單 ↔ 實際 `tools/` 檔案 parity guard |
| `tools/tests/test_discovery_parity.py` | 三支工具的 notebook-discovery 行為 parity（converter / sync / validator 枚舉同一組 `.ipynb`） |

## 失敗時怎麼修

| 症狀 | 修法 |
|------|------|
| sync check 報 `DRIFT` | `python3 tools/ipynb_to_py.py .` 重生 `.py`，再 `git add` 一起 commit |
| sync check 報 `MISSING` | 同上，缺的 `.py` 會被生出來 |
| sync check 報 `ORPHAN`（`.py` 沒有對應 `.ipynb`） | notebook 確實要刪 → `git rm <orphan>.py`；notebook 被誤刪 → `git checkout HEAD~1 -- <nb>.ipynb` 再重生 |
| converted check 報 compile failure / magic leak | 通常是 converter 規則漂移；重生 `.py` 後若仍失敗，檢查該 notebook 的 cell 內容 |
| `--strict` 報 `[strict] N notebook(s) failed` | 有 notebook 是壞 JSON；修好該 `.ipynb` 再跑 |
