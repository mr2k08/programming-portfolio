import sys, os, pickle, tempfile
import numpy as np
import pandas as pd
import lightgbm as lgb

from PyQt6.QtCore import Qt, QAbstractTableModel
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtWidgets import (
    QApplication, QWidget, QFileDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLabel, QLineEdit, QComboBox, QGroupBox, QFormLayout, QMessageBox,
    QTableView, QMainWindow, QDialog, QTextBrowser, QStackedWidget, QSpinBox
)

FEATURE_WEIGHTS = {
    "deal_value_usd": 5,
    "dealval_buyerrev": 3,
    "debt_financing_pct": 4,
    "earnout_flag": 5,
    "industry_match": 4,
    "geo_match": 2,
    "language_match": 2,
    "ebitda_ratio": 6,
    "stake": 3,
}
BLEND_ALPHA = 0.35

def canon_buyer_region(val:str)->str:
    m = {"NA":"NORTH_AMERICA","APAC":"ASIA_PACIFIC","EU":"EUROPE","MEA":"MIDDLE_EAST_AFRICA","LATAM":"LATAM"}
    return m.get(str(val).upper(), "OTHER")

def canon_seller_region(val:str)->str:
    m = {
        "EAST":"ASIA_PACIFIC","WEST":"NORTH_AMERICA","NORTH":"EUROPE","SOUTH":"LATAM",
        "EUROPE":"EUROPE","ASIA":"ASIA_PACIFIC","MIDDLE_EAST":"MIDDLE_EAST_AFRICA","AFRICA":"MIDDLE_EAST_AFRICA",
        "NORTH AMERICA":"NORTH_AMERICA","SOUTH AMERICA":"LATAM"
    }
    return m.get(str(val).upper(), "OTHER")

def lang_code(country:str)->str:
    d = {'US':'EN','UK':'EN','CA':'EN','IN':'EN','AE':'AR','SA':'AR','FR':'FR','DE':'DE','ES':'ES','JP':'JA','CN':'ZH'}
    return d.get(str(country).upper(), 'EN')

def stake_bucket(pct: float) -> str:
    if pct >= 100: return "Full"
    if pct > 50:   return "Majority"
    return "Minority"

def build_features_row(s: pd.Series, b: pd.Series) -> dict:
    ask   = float(s['ask_price'])
    rev   = float(b['annual_revenue'])
    budg  = float(b['budget_max'])
    ebit  = float(s['seller_ebitda'])
    profit= float(s['seller_net_profit'])
    ev    = float(s['seller_ev'])
    stake = float(s['stake_pct'])
    return {
        "deal_value_usd": ask,
        "dealval_buyerrev": ask/(rev+1e-6),
        "debt_financing_pct": float(np.clip(100.0 * max((ask-budg)/(ask+1e-6),0),0,100)),
        "earnout_flag": int((ask > budg) or (rev < 0.5*ask)),
        "industry_match": int(str(s['industry_code']) == str(b['industry_code'])),
        "geo_match": int(canon_seller_region(s.get("geo_region", s['country'])) == canon_buyer_region(b['region'])),
        "language_match": int(lang_code(s['country']) == lang_code(b['country'])),
        "ebitda_ratio": (ebit+1e-6)/(ask+1e-6),
        "affordability_ratio": budg/(ask+1e-6),
        "pe_ratio": (ev/(stake/100.0)+1e-6)/(profit+1e-6),
        "ev_to_ebitda": (ev+1e-6)/(ebit+1e-6),
        "buyer_type": str(b["buyer_type"]),
        "seller_type": str(s["seller_type"]),
        "stake": stake_bucket(stake),
    }

def _minmax01(series: pd.Series) -> pd.Series:
    mn, mx = float(series.min()), float(series.max())
    if not np.isfinite(mn) or not np.isfinite(mx) or mx <= mn:
        return pd.Series([0.5] * len(series), index=series.index)
    return (series - mn) / (mx - mn)

def compute_rule_score(df_raw: pd.DataFrame) -> pd.Series:
    s = pd.Series(0.0, index=df_raw.index, dtype=float)

    def add_feat(name: str, v: pd.Series, transform: str = 'minmax', invert: bool = False, clip_min=None, clip_max=None):
        if name not in FEATURE_WEIGHTS or v is None:
            return
        v = pd.to_numeric(v, errors='coerce')
        if clip_min is not None or clip_max is not None:
            v = v.clip(lower=clip_min if clip_min is not None else v.min(),
                       upper=clip_max if clip_max is not None else v.max())
        if transform == 'ratio_inv':
            v = 1.0 / (1.0 + v.clip(lower=0))
        elif transform == 'one_minus':
            v = 1.0 - v
        if v.max() == v.min() or v.isna().all():
            return
        v = _minmax01(v.fillna(v.median()))
        if invert:
            v = 1.0 - v
        s[:] = s.values + FEATURE_WEIGHTS[name] * v.values

    if 'deal_value_usd' in df_raw:
        add_feat('deal_value_usd', df_raw['deal_value_usd'], transform='minmax')
    if 'dealval_buyerrev' in df_raw:
        add_feat('dealval_buyerrev', df_raw['dealval_buyerrev'], transform='ratio_inv')
    if 'debt_financing_pct' in df_raw:
        add_feat('debt_financing_pct', df_raw['debt_financing_pct'] / 100.0, transform='one_minus', clip_min=0, clip_max=1)
    if 'earnout_flag' in df_raw:
        add_feat('earnout_flag', df_raw['earnout_flag'].astype(float).clip(0, 1), transform='one_minus')
    for k in ('industry_match', 'geo_match', 'language_match'):
        if k in df_raw:
            add_feat(k, df_raw[k].astype(float).clip(0, 1), transform='minmax')
    if 'ebitda_ratio' in df_raw:
        add_feat('ebitda_ratio', df_raw['ebitda_ratio'].astype(float).clip(0, 1.5), transform='minmax')
    if 'stake' in df_raw:
        mapping = {'Full': 1.0, 'Majority': 0.75, 'Minority': 0.45}
        add_feat('stake', df_raw['stake'].map(mapping).fillna(0.6), transform='minmax')

    return _minmax01(s)

class DataFrameModel(QAbstractTableModel):
    def __init__(self, df: pd.DataFrame):
        super().__init__()
        self._df = df.copy()
    def rowCount(self, parent=None): return len(self._df)
    def columnCount(self, parent=None): return len(self._df.columns)
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole: return None
        val = self._df.iat[index.row(), index.column()]
        return "" if pd.isna(val) else str(val)
    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole: return None
        if orientation == Qt.Orientation.Horizontal: return self._df.columns[section]
        return str(section)

class TableWindow(QMainWindow):
    def __init__(self, df: pd.DataFrame, title: str):
        super().__init__()
        self.setWindowTitle(title)
        view = QTableView()
        view.setModel(DataFrameModel(df))
        view.resizeColumnsToContents()
        self.setCentralWidget(view)
        self.resize(1100, 650)

class MatcherGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Deal Matcher")
        self.resize(1200, 820)
        self._dark_blue_theme()

        self.model_file = "deal_success_clean.txt"
        self.meta_file  = "deal_success_meta.pkl"
        self.train_cols = None
        self.cat_maps   = None
        self.last_details = None

        self.deals_path   = QLineEdit();  self.deals_path.setMinimumWidth(800)
        self.buyers_path  = QLineEdit();  self.buyers_path.setMinimumWidth(800)
        self.sellers_path = QLineEdit();  self.sellers_path.setMinimumWidth(800)
        btn_deals   = QPushButton("Select Deals XLSX")
        btn_buyers  = QPushButton("Select Buyers XLSX")
        btn_sellers = QPushButton("Select Sellers XLSX")
        btn_deals.clicked.connect(lambda: self._pick(self.deals_path, "Excel Files (*.xlsx)"))
        btn_buyers.clicked.connect(lambda: self._pick(self.buyers_path, "Excel Files (*.xlsx)"))
        btn_sellers.clicked.connect(lambda: self._pick(self.sellers_path, "Excel Files (*.xlsx)"))

        self.mode = QComboBox(); self.mode.addItems(["Seller → Buyers", "Buyer → Sellers"])
        self.mode.setMinimumWidth(320)
        self.target = QLineEdit(); self.target.setPlaceholderText("Seller name (if Seller→Buyers) or Buyer ID (if Buyer→Sellers)")
        self.target.setMinimumWidth(800)
        try:
            self.target.setAlignment(Qt.AlignmentFlag.AlignLeft)
        except Exception:
            pass

        btn_train  = QPushButton("Train (shows stats)")
        btn_rank   = QPushButton("Rank (only)")
        btn_clear  = QPushButton("Clear Output")
        btn_detail = QPushButton("Open Top-N Details")
        btn_detail.setEnabled(False)
        btn_help   = QPushButton("How to Use")
        btn_train.clicked.connect(self.train_only)
        btn_rank.clicked.connect(self.rank_only)
        btn_clear.clicked.connect(self.clear_output)
        btn_detail.clicked.connect(self.open_details)
        btn_help.clicked.connect(self.show_help)
        self.btn_detail = btn_detail

        self.top_n = QSpinBox(); self.top_n.setRange(1, 5000); self.top_n.setValue(10); self.top_n.setFixedWidth(90)

        self.out = QTextEdit(); self.out.setReadOnly(True)
        self.out.setStyleSheet("font-family: Menlo, Consolas, monospace; font-size: 12px;")

        files = QGroupBox("Files")
        fl = QFormLayout()
        fl.addRow(QLabel("Deals XLSX:"), self.deals_path); fl.addRow(btn_deals)
        fl.addRow(QLabel("Buyers XLSX:"), self.buyers_path); fl.addRow(btn_buyers)
        fl.addRow(QLabel("Sellers XLSX:"), self.sellers_path); fl.addRow(btn_sellers)
        files.setLayout(fl)

        cfg = QGroupBox("Mode")
        cl = QFormLayout()
        cl.addRow(QLabel("Compare:"), self.mode)
        cl.addRow(QLabel("Target:"), self.target)
        cfg.setLayout(cl)

        row = QHBoxLayout()
        row.addWidget(btn_train)
        row.addWidget(btn_rank)
        row.addWidget(btn_clear)
        row.addWidget(QLabel("Top N:"))
        row.addWidget(self.top_n)
        row.addWidget(btn_detail)
        row.addWidget(btn_help)
        row.addStretch(1)

        root = QVBoxLayout()
        root.addWidget(files); root.addWidget(cfg); root.addLayout(row); root.addWidget(self.out, 1)

        main_page = QWidget(); main_page.setLayout(root)
        home_page = self._build_home()

        self.pages = QStackedWidget()
        self.pages.addWidget(home_page)
        self.pages.addWidget(main_page)

        nav = QHBoxLayout()
        btn_home = QPushButton("Home")
        btn_app  = QPushButton("Matcher")
        btn_home.clicked.connect(lambda: self.pages.setCurrentIndex(0))
        btn_app.clicked.connect(lambda: self.pages.setCurrentIndex(1))
        nav.addWidget(btn_home); nav.addWidget(btn_app); nav.addStretch(1)

        top = QVBoxLayout()
        top.addLayout(nav)
        top.addWidget(self.pages, 1)
        self.setLayout(top)

        self.last_ranking = None
        self.last_details_df = None
        self.last_id_col = None
        self.last_title = None

    def _dark_blue_theme(self):
        pal = QPalette()
        pal.setColor(QPalette.ColorRole.Window, QColor(255,255,255))
        pal.setColor(QPalette.ColorRole.Base, QColor(255,255,255))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor(245,247,250))
        pal.setColor(QPalette.ColorRole.Text, QColor(17,24,39))
        pal.setColor(QPalette.ColorRole.WindowText, QColor(17,24,39))
        pal.setColor(QPalette.ColorRole.Button, QColor(245,247,251))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor(17,24,39))
        pal.setColor(QPalette.ColorRole.Highlight, QColor(41,98,255))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor(255,255,255))
        self.setPalette(pal)
        self.setStyleSheet("""
            QPushButton { padding: 8px 12px; border: 1px solid #cfd8e3; border-radius: 6px; background:#f5f7fb; color:#111827; }
            QPushButton:hover { background:#e9edf7; }
            QGroupBox { border: 1px solid #d1d5db; border-radius: 6px; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; color:#374151; }
            QLineEdit, QComboBox { padding: 6px; border: 1px solid #cbd5e1; border-radius:4px; background:#ffffff; color:#111827; }
            /* Combo popup list should be light with dark text */
            QComboBox QAbstractItemView { background:#ffffff; color:#111827; border: 1px solid #cbd5e1; selection-background-color:#e5e7eb; selection-color:#111827; }
            /* SpinBox styling for white background and black text */
            QSpinBox { padding: 4px 6px; border: 1px solid #cbd5e1; border-radius:4px; background:#ffffff; color:#111827; }
            QSpinBox QLineEdit { background:#ffffff; color:#111827; border: none; }
            QSpinBox::up-button, QSpinBox::down-button { background:#f3f4f6; border-left: 1px solid #cbd5e1; width:18px; }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover { background:#e5e7eb; }
            QLabel { color: #111827; }
            QTextEdit { background:#ffffff; color:#111827; border:1px solid #cbd5e1; border-radius:6px; }
        """)

    def _pick(self, line: QLineEdit, filt: str):
        p, _ = QFileDialog.getOpenFileName(self, "Select File", "", filt)
        if p: line.setText(p)

    def _err(self, msg:str):
        QMessageBox.critical(self, "Error", msg)

    def log(self, s:str):
        self.out.append(s)

    def clear_output(self):
        self.out.clear(); self.last_details=None; self.btn_detail.setEnabled(False)
        self.last_ranking = None; self.last_details_df = None; self.last_id_col = None; self.last_title = None

    def show_help(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("How to Use — Deal Matcher")
        dlg.resize(820, 560)
        browser = QTextBrowser(dlg)
        browser.setOpenExternalLinks(True)
        browser.setStyleSheet("font-size: 13px;")
        browser.setHtml(self._help_html())
        layout = QVBoxLayout()
        layout.addWidget(browser)
        dlg.setLayout(layout)
        dlg.exec()

    def _help_html(self) -> str:
        return (
            """
            <h2>Deal Matcher — How to Use</h2>
            <p>This tool trains a LightGBM model on historical deals and ranks the best matching counterparties based on a selected target.</p>

            <h3>1) Prepare Your Files</h3>
            <ul>
              <li><b>Deals XLSX</b>: Historical transactions with a <code>success_flag</code> column (0/1) and feature columns.</li>
              <li><b>Buyers XLSX</b>: Runtime buyers to match. Must include keys like <code>buyer_id</code>, <code>industry_code</code>, <code>region</code>, <code>country</code>, <code>annual_revenue</code>, <code>budget_max</code>, <code>buyer_type</code>.</li>
              <li><b>Sellers XLSX</b>: Runtime sellers to match, provided in the <code>Sellers_Data</code> sheet. Include keys like <code>seller_id</code>, <code>seller_name</code>, <code>industry_code</code>, <code>country</code>, <code>geo_region</code>, <code>seller_ebitda</code>, <code>seller_net_profit</code>, <code>seller_ev</code>, <code>stake_pct</code>, <code>seller_type</code>, <code>ask_price</code>.</li>
            </ul>

            <h3>2) Train the Model</h3>
            <ol>
              <li>Click <b>Select Deals XLSX</b> and choose your labeled training file.</li>
              <li>Click <b>Train (only)</b>. The model and metadata are saved locally as <code>deal_success_clean.txt</code> and <code>deal_success_meta.pkl</code>.</li>
            </ol>

            <h3>3) Choose Mode and Target</h3>
            <ul>
              <li><b>Seller → Buyers</b>: Enter a seller name that exists in <code>Sellers_Data</code> (column <code>seller_name</code>).</li>
              <li><b>Buyer → Sellers</b>: Enter a buyer ID found in the Buyers file (column <code>buyer_id</code>).</li>
            </ul>

            <h3>4) Rank Matches</h3>
            <ol>
              <li>Select your <b>Buyers XLSX</b> and <b>Sellers XLSX</b>.</li>
              <li>Click <b>Rank (only)</b>. Top-N results (as per selector) appear.</li>
              <li>Click <b>Open Top-N Details</b> to export an Excel file with details, open it, and print in the console.</li>
            </ol>

            <h3>Notes</h3>
            <ul>
              <li>The feature builder expects sensible numeric fields; non-numeric entries are coerced when possible.</li>
              <li>During runtime, categoricals are mapped based on the training mapping; unseen values default to -1.</li>
              <li>If Excel is unavailable, the app saves the XLSX to a temp path and shows a fallback table viewer.</li>
            </ul>

            <p style="color:#9bbcff">Tip: Ensure column names match exactly; otherwise, training or ranking may fail with a helpful error.</p>
            """
        )

    def _build_home(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        intro = QTextBrowser()
        intro.setOpenExternalLinks(True)
        intro.setStyleSheet("font-size: 16px;")
        intro.setHtml(self._home_html())
        btn_manual = QPushButton("How to Use")
        btn_manual.clicked.connect(self.show_help)
        buttons = QHBoxLayout(); buttons.addStretch(1); buttons.addWidget(btn_manual); buttons.addStretch(1)
        lay.addStretch(1)
        lay.addWidget(intro)
        lay.addSpacing(8)
        lay.addLayout(buttons)
        lay.addStretch(2)
        return w

    def _home_html(self) -> str:
        return (
            """
            <div style='text-align:center'>
              <h1 style='font-size:36px; margin: 12px 0 4px 0;'>Deal Matcher</h1>
              <div style='color:#9bbcff; font-size:16px; margin-bottom: 12px;'>Find your best Buyer/Seller matches</div>
              <p style='margin: 0; opacity: 0.9;'>Go to <b>Matcher</b> to start.</p>
              <p style='margin: 4px 0 0 0; opacity: 0.8;'>Need guidance? Open <b>How to Use</b>.</p>
            </div>
            """
        )

    def train_only(self):
        deals = self.deals_path.text().strip()
        if not deals: return self._err("Select a Deals XLSX.")

        try:
            if deals.lower().endswith('.csv'):
                df = pd.read_csv(deals)
            else:
                df = pd.read_excel(deals)
        except Exception as e:
            return self._err(f"Failed to read Deals XLSX:\n{e}")
        if 'success_flag' not in df.columns:
            return self._err("Deals XLSX must include 'success_flag'.")

        X = df.drop(columns=['success_flag'])
        y = df['success_flag'].astype(int)

        cat_maps = {}
        for c in X.columns:
            if X[c].dtype == 'object':
                codes, uniques = pd.factorize(X[c], sort=True)
                X[c] = codes.astype(float)
                cat_maps[c] = [str(u) for u in uniques.tolist()]

        from sklearn.model_selection import train_test_split
        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
        train_ds = lgb.Dataset(X_tr, y_tr)
        valid_ds = lgb.Dataset(X_te, y_te, reference=train_ds)

        params = dict(
            objective='binary',
            learning_rate=0.05,
            num_leaves=63,
            feature_fraction=0.9,
            bagging_fraction=0.8,
            bagging_freq=1,
            metric=['binary_logloss','auc'],
            verbosity=-1,
            seed=42
        )

        model = lgb.train(
            params, train_ds,
            num_boost_round=2000,
            valid_sets=[train_ds, valid_ds],
            valid_names=['train','test'],
            callbacks=[lgb.early_stopping(75, verbose=False)]
        )

        proba = model.predict(X_te)
        from sklearn.metrics import accuracy_score, log_loss, roc_auc_score
        acc = accuracy_score(y_te, (proba>0.5).astype(int))

        model.save_model(self.model_file)
        with open(self.meta_file, "wb") as f:
            pickle.dump({"columns": list(X.columns), "categoricals": cat_maps}, f)

        self.train_cols = list(X.columns)
        self.cat_maps   = cat_maps

        self.log(f"TRAIN DONE → saved {self.model_file}")
        self.log(f"Accuracy: {acc:.4f}")
        self.log(f"Log loss: {log_loss(y_te, proba):.4f}")
        self.log(f"ROC-AUC : {roc_auc_score(y_te, proba):.4f}")

    def rank_only(self):
        buyers  = self.buyers_path.text().strip()
        sellers = self.sellers_path.text().strip()
        if not buyers or not sellers:
            return self._err("Select Buyers XLSX and Sellers XLSX.")

        try:
            booster = lgb.Booster(model_file=self.model_file)
            with open(self.meta_file, "rb") as f:
                meta = pickle.load(f)
            train_cols = meta["columns"]; cat_maps = meta["categoricals"]
        except Exception as e:
            return self._err(f"Load model/meta failed. Train first.\n{e}")

        try:
            buyers_df  = pd.read_excel(buyers) if not buyers.lower().endswith('.csv') else pd.read_csv(buyers)
            if sellers.lower().endswith('.csv'):
                sellers_df = pd.read_csv(sellers)
            else:
                sellers_df = pd.read_excel(sellers, sheet_name='Sellers_Data')
        except Exception as e:
            return self._err(f"Failed to read runtime files:\n{e}")

        mode   = 's' if self.mode.currentText().startswith("Seller") else 'b'
        target = self.target.text().strip()
        if not target: return self._err("Enter Target.")

        if mode == 's':
            if target not in set(sellers_df['seller_name'].astype(str)):
                return self._err(f"Seller '{target}' not found.")
            anchor = sellers_df.loc[sellers_df['seller_name'].astype(str)==target].iloc[0]
            pairs  = [(anchor, b) for _, b in buyers_df.iterrows()]
            id_col = 'buyer_id'
            ids    = [b['buyer_id'] for _, b in pairs]
            title  = f"Top buyers for seller: {anchor['seller_name']}"
            details_df = buyers_df.copy()
        else:
            if target not in set(buyers_df['buyer_id'].astype(str)):
                return self._err(f"Buyer '{target}' not found.")
            anchor = buyers_df.loc[buyers_df['buyer_id'].astype(str)==target].iloc[0]
            pairs  = [(s, anchor) for _, s in sellers_df.iterrows()]
            id_col = 'seller_id'
            ids    = [s['seller_id'] for s, _ in pairs]
            title  = f"Top sellers for buyer: {anchor['buyer_id']}"
            details_df = sellers_df.copy()

        rows = [build_features_row(s, b) for (s, b) in pairs]
        feat_raw = pd.DataFrame(rows)
        rule_score = compute_rule_score(feat_raw)
        feat = feat_raw.copy()

        for c, cats in cat_maps.items():
            if c in feat.columns:
                mapping = {str(cat): i for i, cat in enumerate(cats)}
                feat[c] = feat[c].astype(str).map(mapping).fillna(-1).astype(float)

        for c in feat.columns:
            if feat[c].dtype == 'object':
                feat[c] = pd.factorize(feat[c])[0].astype(float)

        for c in train_cols:
            if c not in feat.columns: feat[c] = 0.0
        feat = feat[train_cols]

        model_score = booster.predict(feat)
        final_score = (1.0 - BLEND_ALPHA) * model_score + BLEND_ALPHA * rule_score.values
        ranking = (
            pd.DataFrame({
                id_col: ids,
                'model_score': model_score,
                'rule_score': rule_score.values,
                'final_score': final_score,
            })
            .sort_values('final_score', ascending=False)
            .reset_index(drop=True)
        )

        self.last_ranking = ranking
        self.last_details_df = details_df
        self.last_id_col = id_col
        self.last_title = title
        self.btn_detail.setEnabled(True)

        n = int(self.top_n.value())
        self.log(f"\n{title} (Top {n})")
        self.log(ranking.head(n).to_string(index=False))

    def open_details(self):
        if self.last_ranking is None or self.last_details_df is None or self.last_id_col is None:
            return self._err("No ranking to show. Run Rank first.")
        try:
            n = int(self.top_n.value())
            topn = self.last_ranking.head(n)
            try:
                details = topn.merge(self.last_details_df, on=self.last_id_col, how='left')
            except Exception:
                details = topn

            tmp = tempfile.NamedTemporaryFile(prefix="topn_", suffix=".xlsx", delete=False)
            tmp_path = tmp.name
            tmp.close()
            details.to_excel(tmp_path, index=False)

            try:
                os.system(f'open -a "Microsoft Excel" "{tmp_path}"')
                self.log(f"Opened Top-{n} XLSX in Excel: {tmp_path}")
            except Exception:
                self.log(f"Saved Top-{n} XLSX (open manually): {tmp_path}")
                self.tw = TableWindow(details, f"Top-{n} Details (fallback view)")
                self.tw.show()

            title = self.last_title or "Top matches"
            self.log(f"\n{title} (Top {n})")
            self.log(topn.to_string(index=False))
        except Exception as e:
            self._err(f"Failed to export/open XLSX:\n{e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = MatcherGUI()
    gui.show()
    sys.exit(app.exec())

'''
/Users/Programing/ML/buyerSellerProject/data/transactions/deals_training_labeled_v5.xlsx
/Users/Programing/ML/buyerSellerProject/data/Buyers/buyers_runtime_v5.xlsx
/Users/Programing/ML/buyerSellerProject/data/Sellers/sellers_simulated_v5.xlsx
'''
