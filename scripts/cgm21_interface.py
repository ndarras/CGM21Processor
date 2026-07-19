import json
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

APP_ROOT = Path(__file__).resolve().parents[1]
IS_FROZEN = bool(getattr(sys, "frozen", False))
PYCGM2_PYTHON = Path(sys.executable) if IS_FROZEN else Path(r"C:\Users\darra\miniconda3\envs\pycgm310\python.exe")
PROCESS_SCRIPT = APP_ROOT / "scripts" / "process_cgm21.py"
TEMPLATE_CONFIG = APP_ROOT / "cgm21_config.json"

REQUIRED_MP = [
    "Bodymass",
    "LeftLegLength",
    "RightLegLength",
    "LeftKneeWidth",
    "RightKneeWidth",
    "LeftAnkleWidth",
    "RightAnkleWidth",
    "LeftSoleDelta",
    "RightSoleDelta",
    "LeftShoulderOffset",
    "LeftElbowWidth",
    "LeftWristWidth",
    "LeftHandThickness",
    "RightShoulderOffset",
    "RightElbowWidth",
    "RightWristWidth",
    "RightHandThickness",
]

OPTIONAL_MP = [
    "InterAsisDistance",
    "LeftAsisTrocanterDistance",
    "LeftTibialTorsion",
    "LeftThighRotation",
    "LeftShankRotation",
    "RightAsisTrocanterDistance",
    "RightTibialTorsion",
    "RightThighRotation",
    "RightShankRotation",
]

FILTERS = [
    "markerCutoffHz",
    "markerOrder",
    "forcePlateCutoffHz",
    "forcePlateOrder",
]

TRANSLATORS = ["LTOE", "RTOE", "LPSI", "RPSI"]

DEFAULT_CONFIG = {
    "notes": [
        "Units are millimetres except Bodymass in kg.",
        "Edit these values before processing if the C3D metadata does not contain subject anthropometrics.",
    ],
    "markerDiameter": 14.0,
    "leftFlatFoot": False,
    "rightFlatFoot": False,
    "headFlat": False,
    "momentProjection": "Distal",
    "translators": {"LTOE": "LLA_TOE", "RTOE": "RLA_TOE", "LPSI": "SACR", "RPSI": "SACR"},
    "required_mp": {key: 0.0 for key in REQUIRED_MP},
    "optional_mp": {key: 0.0 for key in OPTIONAL_MP},
    "applyFilters": False,
    "filters": {"markerCutoffHz": 6.0, "markerOrder": 4, "forcePlateCutoffHz": 6.0, "forcePlateOrder": 4},
    "forcePlateAssignment": "AUTO",
    "exportMokkaReviewFiles": False,
}


class Cgm21Interface(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CGM2.1 Processor")
        self.geometry("980x720")
        self.minsize(820, 560)

        self.folder_var = tk.StringVar(value=str(APP_ROOT))
        self.status_var = tk.StringVar(value="Select a folder containing C3D files. Files with static in the name are static trials; all others are dynamic.")
        self.config_path_var = tk.StringVar(value="")
        self.config_data = {}
        self.entry_vars = {}
        self.bool_vars = {}
        self.moment_projection_var = tk.StringVar(value="Distal")
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_text_var = tk.StringVar(value="Progress: idle")
        self.progress_count_var = tk.StringVar(value="0 / 0")

        self._build_ui()
        self.load_config_for_selected_folder(silent=True)

    def _build_ui(self):
        outer = tk.Frame(self, padx=14, pady=14)
        outer.pack(fill=tk.BOTH, expand=True)

        tk.Label(outer, text="C3D folder").pack(anchor=tk.W)
        picker = tk.Frame(outer)
        picker.pack(fill=tk.X, pady=(4, 8))
        tk.Entry(picker, textvariable=self.folder_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(picker, text="Browse", command=self.browse).pack(side=tk.LEFT, padx=(8, 0))

        actions = tk.Frame(outer)
        actions.pack(fill=tk.X, pady=(0, 8))
        self.run_button = tk.Button(actions, text="Run CGM2.1", command=self.run_processing, height=2)
        self.run_button.pack(side=tk.LEFT)
        tk.Button(actions, text="Load Config", command=lambda: self.load_config_for_selected_folder(silent=False)).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(actions, text="Save Config", command=self.save_config_from_fields).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(actions, text="Open Processed Folder", command=self.open_processed).pack(side=tk.LEFT, padx=(8, 0))

        tk.Label(outer, textvariable=self.status_var, anchor="w").pack(fill=tk.X, pady=(0, 4))
        tk.Label(outer, textvariable=self.config_path_var, anchor="w", fg="#555555").pack(fill=tk.X, pady=(0, 8))
        progress_panel = tk.Frame(outer)
        progress_panel.pack(fill=tk.X, pady=(0, 8))
        tk.Label(progress_panel, textvariable=self.progress_text_var, anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(progress_panel, textvariable=self.progress_count_var, width=10, anchor="e").pack(side=tk.RIGHT)
        self.progress_bar = ttk.Progressbar(outer, variable=self.progress_var, maximum=100.0)
        self.progress_bar.pack(fill=tk.X, pady=(0, 8))

        notebook = ttk.Notebook(outer)
        notebook.pack(fill=tk.BOTH, expand=True)

        config_tab = tk.Frame(notebook)
        log_tab = tk.Frame(notebook)
        notebook.add(config_tab, text="Config")
        notebook.add(log_tab, text="Run Log")

        self._build_config_tab(config_tab)
        self.log = scrolledtext.ScrolledText(log_tab, wrap=tk.WORD, height=20)
        self.log.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.log.configure(state=tk.DISABLED)

    def _build_config_tab(self, parent):
        canvas = tk.Canvas(parent, highlightthickness=0)
        scroll = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        body = tk.Frame(canvas)
        body.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=body, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._section(body, "General")
        self._entry(body, "markerDiameter", "Marker diameter (mm)")
        self._entry(body, "forcePlateAssignment", "Force plates (AUTO, ORIGINAL_AUTO, or L/R/X)")
        self._option(body, "momentProjection", "Moment projection", ["Distal", "Proximal", "Global", "JCS"])
        self._check(body, "applyFilters", "Apply pyCGM2 marker/force filters")
        self._check(body, "leftFlatFoot", "Left flat foot")
        self._check(body, "rightFlatFoot", "Right flat foot")
        self._check(body, "headFlat", "Head flat")

        self._section(body, "Required Anthropometrics")
        for key in REQUIRED_MP:
            label = f"{key} ({'kg' if key == 'Bodymass' else 'mm'})"
            self._entry(body, f"required_mp.{key}", label)

        self._section(body, "Optional Anthropometrics")
        for key in OPTIONAL_MP:
            self._entry(body, f"optional_mp.{key}", f"{key} (mm or degrees)")

        self._section(body, "Filters")
        for key in FILTERS:
            self._entry(body, f"filters.{key}", key)

        self._section(body, "Marker Translators")
        for key in TRANSLATORS:
            self._entry(body, f"translators.{key}", key)

    def _section(self, parent, text):
        tk.Label(parent, text=text, font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, padx=8, pady=(12, 4))

    def _entry(self, parent, key, label):
        row = tk.Frame(parent)
        row.pack(fill=tk.X, padx=8, pady=2)
        tk.Label(row, text=label, width=32, anchor="w").pack(side=tk.LEFT)
        var = tk.StringVar()
        self.entry_vars[key] = var
        tk.Entry(row, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _check(self, parent, key, label):
        var = tk.BooleanVar(value=False)
        self.bool_vars[key] = var
        tk.Checkbutton(parent, text=label, variable=var).pack(anchor=tk.W, padx=8, pady=2)

    def _option(self, parent, key, label, options):
        row = tk.Frame(parent)
        row.pack(fill=tk.X, padx=8, pady=2)
        tk.Label(row, text=label, width=32, anchor="w").pack(side=tk.LEFT)
        ttk.Combobox(row, textvariable=self.moment_projection_var, values=options, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True)

    def browse(self):
        folder = filedialog.askdirectory(initialdir=self.folder_var.get() or str(APP_ROOT))
        if folder:
            self.folder_var.set(folder)
            self.status_var.set("Ready.")
            self.load_config_for_selected_folder(silent=True)

    def append_log(self, text):
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, text)
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def reset_progress(self):
        self.progress_var.set(0.0)
        self.progress_text_var.set("Progress: starting")
        self.progress_count_var.set("0 / 0")

    def handle_progress_line(self, line):
        if not line.startswith("::progress::"):
            return False
        try:
            payload = line.strip().split("::progress::", 1)[1]
            count_part, message = payload.split("::", 1)
            done_text, total_text = count_part.split("/", 1)
            done = int(done_text)
            total = max(int(total_text), 1)
            percent = min(100.0, max(0.0, done / total * 100.0))
            self.progress_var.set(percent)
            self.progress_count_var.set(f"{done} / {total}")
            self.progress_text_var.set(message)
            return True
        except Exception:
            return False

    def selected_folder(self):
        return Path(self.folder_var.get()).expanduser().resolve()

    def config_path_for_folder(self, folder):
        return folder / "cgm21_config.json"

    def read_template_config(self):
        if TEMPLATE_CONFIG.exists():
            return json.loads(TEMPLATE_CONFIG.read_text(encoding="utf-8"))
        return json.loads(json.dumps(DEFAULT_CONFIG))

    def ensure_config_file(self, folder):
        config_path = self.config_path_for_folder(folder)
        if not config_path.exists():
            config_path.write_text(json.dumps(self.read_template_config(), indent=2), encoding="utf-8")
        return config_path

    def load_config_for_selected_folder(self, silent=False):
        try:
            folder = self.selected_folder()
            if not folder.is_dir():
                raise ValueError("Selected path is not a folder.")
            config_path = self.ensure_config_file(folder)
            self.config_data = json.loads(config_path.read_text(encoding="utf-8"))
            self.populate_fields()
            self.config_path_var.set(f"Config: {config_path}")
            if not silent:
                self.status_var.set("Config loaded.")
        except Exception as exc:
            if not silent:
                messagebox.showerror("Load config", str(exc))

    def populate_fields(self):
        data = self.config_data
        for key, var in self.entry_vars.items():
            value = self.get_nested(data, key, "")
            var.set(str(value))
        for key, var in self.bool_vars.items():
            var.set(bool(data.get(key, False)))
        self.moment_projection_var.set(str(data.get("momentProjection", "Distal")))

    def get_nested(self, data, dotted, default=None):
        current = data
        for part in dotted.split("."):
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current

    def set_nested(self, data, dotted, value):
        parts = dotted.split(".")
        current = data
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = value

    def parse_value(self, key, value):
        if key.startswith("translators.") or key == "forcePlateAssignment":
            return value.strip()
        if value.strip() == "":
            return 0.0
        number = float(value)
        if key.endswith("Order") or key in {"filters.markerOrder", "filters.forcePlateOrder"}:
            return int(number)
        return number

    def collect_config_from_fields(self):
        data = self.config_data or self.read_template_config()
        for key, var in self.entry_vars.items():
            self.set_nested(data, key, self.parse_value(key, var.get()))
        for key, var in self.bool_vars.items():
            data[key] = bool(var.get())
        data["momentProjection"] = self.moment_projection_var.get()
        data.setdefault("notes", DEFAULT_CONFIG["notes"])
        return data

    def save_config_from_fields(self):
        try:
            folder = self.selected_folder()
            config_path = self.ensure_config_file(folder)
            data = self.collect_config_from_fields()
            config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            self.config_data = data
            self.config_path_var.set(f"Config: {config_path}")
            self.status_var.set("Config saved.")
            return config_path
        except Exception as exc:
            messagebox.showerror("Save config", str(exc))
            return None

    def classify_c3d_files(self, folder):
        c3d_files = sorted(folder.glob("*.c3d"), key=lambda path: path.name.lower())
        static_files = [path for path in c3d_files if "static" in path.name.lower()]
        dynamic_files = [path for path in c3d_files if "static" not in path.name.lower()]
        return static_files, dynamic_files

    def validate_folder(self, folder):
        if not folder.is_dir():
            raise ValueError("Selected path is not a folder.")
        static_files, dynamic_files = self.classify_c3d_files(folder)
        if not static_files:
            raise ValueError("The selected folder must contain at least one C3D file with 'static' in its filename.")
        if not dynamic_files:
            raise ValueError("The selected folder must contain at least one dynamic C3D file without 'static' in its filename.")

    def prepare_folder(self, folder):
        processed = folder / "processed"
        processed.mkdir(exist_ok=True)
        static_files, dynamic_files = self.classify_c3d_files(folder)
        for trial in [*static_files, *dynamic_files]:
            shutil.copy2(trial, processed / trial.name)
        config = self.save_config_from_fields()
        if config is None:
            raise ValueError("Config was not saved.")
        for name, content in (("cgm21_results.json", "[]"), ("pycgm2-cgm21.log", "")):
            target = processed / name
            if not target.exists():
                target.write_text(content, encoding="utf-8")
        return processed, config

    def run_processing(self):
        folder = self.selected_folder()
        try:
            self.validate_folder(folder)
            processed, config = self.prepare_folder(folder)
        except Exception as exc:
            messagebox.showerror("CGM2.1 setup", str(exc))
            return
        self.run_button.configure(state=tk.DISABLED)
        self.status_var.set("Running CGM2.1...")
        self.reset_progress()
        self.append_log(f"\nRunning original CGM2.1 workflow in: {folder}\n")
        thread = threading.Thread(target=self._run_worker, args=(folder, processed, config), daemon=True)
        thread.start()

    def _run_worker(self, folder, processed, config):
        if IS_FROZEN:
            cmd = [
                str(PYCGM2_PYTHON),
                "--process-cgm21",
                "--input", str(folder),
                "--config", str(config),
                "--output", str(processed),
            ]
        else:
            cmd = [
                str(PYCGM2_PYTHON),
                str(PROCESS_SCRIPT),
                "--input", str(folder),
                "--config", str(config),
                "--output", str(processed),
            ]
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(APP_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                self.after(0, self.handle_progress_line, line)
                self.after(0, self.append_log, line)
            code = proc.wait()
            if code == 0:
                self.after(0, self.progress_var.set, 100.0)
                self.after(0, self.progress_text_var.set, "Processing complete")
                self.after(0, self.status_var.set, f"Done. Files exported to {processed}")
                self.after(0, messagebox.showinfo, "CGM2.1 complete", f"Processed files written to:\n{processed}")
            else:
                self.after(0, self.progress_text_var.set, "Processing failed")
                self.after(0, self.status_var.set, "CGM2.1 failed. Check the log output.")
                self.after(0, messagebox.showerror, "CGM2.1 failed", f"Processing exited with code {code}.")
        except Exception as exc:
            self.after(0, self.progress_text_var.set, "Processing failed")
            self.after(0, self.status_var.set, "CGM2.1 failed. Check the log output.")
            self.after(0, messagebox.showerror, "CGM2.1 failed", str(exc))
        finally:
            self.after(0, self.run_button.configure, {"state": tk.NORMAL})

    def open_processed(self):
        processed = self.selected_folder() / "processed"
        if not processed.exists():
            messagebox.showinfo("Processed folder", "No processed folder exists yet.")
            return
        subprocess.Popen(["explorer", str(processed)])


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--process-cgm21":
        sys.argv = ["process_cgm21.py", *sys.argv[2:]]
        import process_cgm21

        process_cgm21.main()
    else:
        Cgm21Interface().mainloop()


if __name__ == "__main__":
    main()
