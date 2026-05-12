# -*- coding: utf-8 -*-
# Auto-generated from Install TQuant Lab.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# # TQuant Lab 安裝教學
# ## 使用的套件以及環境
#
# * Main package：Zipline
# * 支援的 Python 版本：Python 3.8~3.11（建議使用Python 3.11）
# * 支援的作業系統：Microsoft Windows OS or macOS
# * 建議的 Pandas 版本：1.5.3 或 2.0.0（> 2.0.0 可能會有未預期的錯誤）
# * 建議的 Numpy 版本：1.23.5（> 1.23.5 可能會有未預期的錯誤）
#
# # 以下將提供A、B、C 三種安裝zipline-tej的方式（**擇一即可，但推薦使用方法 A 或 B**）
#
# ---
#
# ## A. 透過docker 安裝 zipline-tej（**推薦**）
#
# #### 先決條件
#
# * 已安裝好docker-desktop
#
# #### 啟動終端機(CMD)
#
# #### (方法一) 透過下載Dockerfile
#
# [下載tquant_jupyter](https://github.com/tejtw/zipline-tej/blob/main/dockerfile/tquant_jupyter) (Jupyter使用)
#
# [下載tquant_bash](https://github.com/tejtw/zipline-tej/blob/main/dockerfile/tquant_bash) (排程使用)
#
# ```
# $ # 於終端機透過 cd 到已下載 dockerfile的目錄之下
# $ docker build -f tquant_jupyter . -t "tquant:latest"
# ```
# #### (方法二) 直接從docker hub下載（**推薦**）
#
# ```
# # 於終端機輸入以下指令
# $ docker pull tej87681088/tquant:latest
# ```
# ### 2 建置一個volume以傳輸雙方資料
#
# ```
# # 於終端機輸入以下指令
# $ docker volume create data
# ```
#
# ### 3. 透過image建置container
#
# ```
# # 於終端機輸入以下指令
# (若透過方法一下載)
# $ docker run -v data:/app -p 8888:8888 --name tquant tquant
# (若透過方法二下載)
# $ docker run -v data:/app -p 8888:8888 --name tquant tej87681088/tquant
# ```
#
# * 此命令將會啟動一個container並將container內部的 8888 埠映射到本機的 8888 埠，並且將可以透過volume傳輸資料
#
# * (以筆者Windows10的電腦為例：volume的位置在 \\\wsl$\docker-desktop-data\data\docker\volumes\data\\_data)
# * (若希望不要保留container，可加入 --rm)
#
# ### 4. 開始使用jupyter
#
# * 此時應該會在終端機看到一串網址類似
#
# ```
# $ http://127.0.0.1:8888/tree?token=XXXXXXXXXXXXXXXX
# ```
#
# * 將其複製並貼上至瀏覽器便可開始使用
#
# ### Appendix
#
# * 若想使用之前已創建過的但關閉的container操作，可透過以下指令取得網址
#
# ```
# # 找尋container ID
# $ docker ps -a 
# # 啟動 指定container
# $ docker start <CONTAINER_ID>
# # 顯示 container 內部終端機最近印出的提示
# $ docker logs --tail 3 <CONTAINER_ID>
# ```
#
# ---
#
# ## B. 透過`Anaconda Prompt`一鍵安裝 zipline-tej（**推薦**）
#
# * 首先，需要下載以下套件文件。
#
#     1. Windows [(zipline-tej.yml)](https://minhaskamal.github.io/DownGit/#/home?url=https://github.com/tejtw/zipline-tej/blob/main/zipline-tej.yml)
#
#     2. Mac [(zipline-tej_mac.yml)](https://minhaskamal.github.io/DownGit/#/home?url=https://github.com/tejtw/zipline-tej/blob/main/zipline-tej_mac.yml)
#
#
# * 接著，在 Anaconda 的命令提示字元中，創建一個虛擬環境並安裝相應版本的依賴套件。我們強烈推薦使用虛擬環境，以保持每個項目的獨立性。[(原因說明)](https://csguide.cs.princeton.edu/software/virtualenv#definition)
#
# ```
#     Window 使用者
#
#     # 將下載好的 zipline-tej.yml檔案放在以下路徑中
#     $ cd <C:\Users\username\Downloads>
#
#     # 透過yml檔安裝所需套件並創建虛擬環境
#     $ conda env create -f zipline-tej.yml
#
#     # 開啟虛擬環境
#     $ conda activate zipline-tej
#
#     Mac 使用者
#     
#     # 將下載好的 zipline-tej.yml檔案放在以下路徑中
#     $ cd \Users\username\Downloads
#
#     # 創建虛擬環境
#     $ conda env create -f zipline-tej_mac.yml
#
#     # 開啟虛擬環境
#     $ conda activate zipline-tej
# ```
#
# * 至此，便可開始使用zipline-tej。
#
# ---
# ## C. 直接透過pip install 安裝 zipline-tej（**使用此方式安裝可能會有未預期的錯誤，可能會需自行 debug**）
#
# * **於本機端安裝 zipline-tej**
#
#     * 在開始安裝之前，我們建議使用 [Anaconda](https://www.anaconda.com/data-science-platform) 作為開發環境。
#
#     * 為避免環境的套件衝突，創建虛擬環境是相當重要的。因此我們建議先建立虛擬環境後，逐一安裝所需的套件。
#
#     * 以下我們建議兩種建立虛擬環境的方式(擇一即可)
#
# ```
#     (方法一)
#     # 透過Anaconda指令
#     # 於Anaconda Prompt
#     # create virtual env
#     $ conda create -n <env_name> python=3.11
#     
#     # activate virtual env
#     $ conda activate <env_name>
#
#     # download packages
#     $ pip install zipline-tej
#     $ pip install notebook
#     $ conda install -c conda-forge nb_conda_kernels
# ```
#
# ```
#     (方法二)
#     # 透過Python原生指令
#     # 於CMD
#     # create virtual env
#     $ python -m venv venv
#
#     # activate virtual env
#     $ venv\Scripts\activate.bat
#     # download packages
#     $ pip install zipline-tej
#     $ pip install notebook
# ```
#
# * **於 google colab 使用 zipline-tej**
#
#     * 若您使用 google colab，可以直接執行以下程式碼，下載 `zipline-tej`。
#
#     <br>
#
#     ```
#       !pip install zipline-tej
#     ```
#
#     <br>
#
#     
#     * 若有使用Pyfolio，可以一併執行下列指令避免出現 Warning。
#
#     <br>
#
#     ```
#       import matplotlib
#       import matplotlib.font_manager as fm
#       !wget -O MicrosoftJhengHei.ttf https://github.com/a7532ariel/ms-web/raw/master/Microsoft-JhengHei.ttf
#       !wget -O ArialUnicodeMS.ttf https://github.com/texttechnologylab/DHd2019BoA/raw/master/fonts/Arial%20Unicode%20MS.TTF
#
#       fm.fontManager.addfont('MicrosoftJhengHei.ttf')
#       matplotlib.rc('font', family='Microsoft Jheng Hei')
#
#       matplotlib.font_manager.fontManager.addfont('ArialUnicodeMS.ttf')
#       matplotlib.rc('font', family='Arial Unicode MS')
#     ```
#
# ## 檢查 zipline-tej 版本
#
# * 若已安裝好zipline-tej，我們可透過以下指令顯示當前zipline-tej的版本。
#
# ```
#   !pip show zipline-tej
# ```
#
# * 為確保當前版本為最新，可以透過以下指令以更新zipline-tej。
#
# ```
#   !pip install --upgrade zipline-tej
# ```
#
# * [zipline-tej當前版本](https://pypi.org/project/zipline-tej/)

# %% [markdown] cell 1
# ## 其他資訊
#
# * [TQuant Lab 官方網站](https://tquant.tejwin.com/)
# * [TQuant Lab Github](https://github.com/tejtw/TQuant-Lab)
