import argparse
import json
import os
import tempfile
import shutil
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]

import numpy as np

import btk

mpl_dir = Path(tempfile.gettempdir()) / "CGM21Processor" / "matplotlib"
mpl_dir.mkdir(parents=True, exist_ok=True)
os.environ["MPLCONFIGDIR"] = str(mpl_dir)

import scipy.integrate

if not hasattr(scipy.integrate, "cumtrapz") and hasattr(scipy.integrate, "cumulative_trapezoid"):
    scipy.integrate.cumtrapz = scipy.integrate.cumulative_trapezoid

# pyCGM2 4.2 imports pyCGM2.btk in some modules. The conda BTK build is the
# working BTK in this environment, so expose it under the module name pyCGM2 expects.
sys.modules["pyCGM2.btk"] = btk

import pyCGM2
from pyCGM2 import enums
from pyCGM2.ForcePlates import forceplates
from pyCGM2.Lib.CGM import cgm2_1
from pyCGM2.Tools import btkTools
from pyCGM2.Utils import files


DEFAULT_CONFIG = APP_ROOT / "cgm21_config.json"
DEFAULT_OUTPUT = APP_ROOT / "processed"

TRANSLATORS = {
    "LTOE": "LLA_TOE",
    "RTOE": "RLA_TOE",
    "LPSI": "SACR",
    "RPSI": "SACR",
}


def emit_progress(done, total, message):
    print(f"::progress::{done}/{total}::{message}", flush=True)


def read_acquisition(path):
    reader = btk.btkAcquisitionFileReader()
    reader.SetFilename(str(path))
    reader.Update()
    return reader.GetOutput()


def classify_c3d_files(folder):
    c3d_files = sorted(folder.glob("*.c3d"), key=lambda path: path.name.lower())
    static_files = [path for path in c3d_files if "static" in path.name.lower()]
    dynamic_files = [path for path in c3d_files if "static" not in path.name.lower()]
    if not static_files:
        raise FileNotFoundError("No static C3D found. Include 'static' in the static trial filename.")
    if not dynamic_files:
        raise FileNotFoundError("No dynamic C3D found. Dynamic trials are C3D files without 'static' in the filename.")
    return static_files, dynamic_files


def point_mean(acq, label):
    values = acq.GetPoint(label).GetValues()
    return np.nanmean(values, axis=0)


def distance(acq, left, right):
    return float(np.linalg.norm(point_mean(acq, left) - point_mean(acq, right)))


def estimate_config(static_path):
    acq = read_acquisition(static_path)
    left_leg = distance(acq, "LASI", "LANK")
    right_leg = distance(acq, "RASI", "RANK")
    return {
        "notes": [
            "Units are millimetres except Bodymass in kg.",
            "Edit these values before processing if the C3D metadata does not contain subject anthropometrics.",
            "The processor calls the original pyCGM2 CGM2.1 calibration and fitting functions without post-processing kinetic outputs.",
            "forcePlateAssignment AUTO derives the local per-trial assignment before fitting, matching the Nexus assignment input used by the original Vicon app.",
            "forcePlateAssignment ORIGINAL_AUTO passes None to pyCGM2 fitting for exact local pyCGM2 auto behavior.",
        ],
        "markerDiameter": 14.0,
        "leftFlatFoot": False,
        "rightFlatFoot": False,
        "headFlat": False,
        "momentProjection": "Distal",
        "translators": TRANSLATORS,
        "required_mp": {
            "Bodymass": 75.0,
            "LeftLegLength": round(left_leg, 1),
            "RightLegLength": round(right_leg, 1),
            "LeftKneeWidth": round(distance(acq, "LKNE", "LMed_kn"), 1),
            "RightKneeWidth": round(distance(acq, "RKNE", "RMed_kn"), 1),
            "LeftAnkleWidth": round(distance(acq, "LANK", "LMed_ank"), 1),
            "RightAnkleWidth": round(distance(acq, "RANK", "RMed_ank"), 1),
            "LeftSoleDelta": 0.0,
            "RightSoleDelta": 0.0,
            "LeftShoulderOffset": 0.0,
            "LeftElbowWidth": 0.0,
            "LeftWristWidth": 0.0,
            "LeftHandThickness": 0.0,
            "RightShoulderOffset": 0.0,
            "RightElbowWidth": 0.0,
            "RightWristWidth": 0.0,
            "RightHandThickness": 0.0,
        },
        "optional_mp": {
            "InterAsisDistance": round(distance(acq, "LASI", "RASI"), 1),
            "LeftAsisTrocanterDistance": 0.0,
            "LeftTibialTorsion": 0.0,
            "LeftThighRotation": 0.0,
            "LeftShankRotation": 0.0,
            "RightAsisTrocanterDistance": 0.0,
            "RightTibialTorsion": 0.0,
            "RightThighRotation": 0.0,
            "RightShankRotation": 0.0,
        },
        "applyFilters": False,
        "filters": {
            "markerCutoffHz": 6.0,
            "markerOrder": 4,
            "forcePlateCutoffHz": 6.0,
            "forcePlateOrder": 4,
        },
        "forcePlateAssignment": "AUTO",
        "exportMokkaReviewFiles": False,
    }


def ensure_config(config_path, input_dir):
    if config_path.exists():
        return
    static_files, _ = classify_c3d_files(input_dir)
    config_path.write_text(json.dumps(estimate_config(static_files[0]), indent=2), encoding="utf-8")


def moment_projection(name):
    return {
        "Distal": enums.MomentProjection.Distal,
        "Proximal": enums.MomentProjection.Proximal,
        "Global": enums.MomentProjection.Global,
        "JCS": enums.MomentProjection.JCS,
    }[name]


def normalize_force_plate_assignment(value):
    if value is None:
        return "AUTO"
    text = str(value).strip().upper()
    if text in {"", "AUTO", "AUTOMATIC"}:
        return "AUTO"
    if text in {"ORIGINAL_AUTO", "PYCGM2_AUTO", "NONE"}:
        return None
    return text


def detect_force_plate_assignment(c3d_path, translators):
    acq = read_acquisition(c3d_path)
    trial_translators = dict(translators)
    if btkTools.isPointExist(acq, "SACR"):
        trial_translators["LPSI"] = "SACR"
        trial_translators["RPSI"] = "SACR"
    acq = btkTools.applyTranslators(acq, trial_translators)
    mapped = forceplates.matchingFootSideOnForceplate(acq, mfpa=None)
    if mapped and set(mapped.upper()) != {"X"}:
        return mapped.upper()
    return None


def copy_trials(input_dir, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    static_files, dynamic_files = classify_c3d_files(input_dir)
    copied = []
    for src in [*static_files, *dynamic_files]:
        dst = output_dir / src.name
        shutil.copy2(src, dst)
        copied.append(dst.name)
    return static_files, dynamic_files, copied


def point_component_max(acq, label):
    if not btkTools.isPointExist(acq, label):
        return None
    values = acq.GetPoint(label).GetValues()
    return [float(np.nanmax(np.abs(values[:, index]))) for index in range(3)]


def collect_dynamic_diagnostics(acq):
    labels = [
        "LGroundReactionForce",
        "RGroundReactionForce",
        "LGroundReactionMoment",
        "RGroundReactionMoment",
        "LHipMoment",
        "LKneeMoment",
        "LAnkleMoment",
        "RHipMoment",
        "RKneeMoment",
        "RAnkleMoment",
        "LHipPower",
        "LKneePower",
        "LAnklePower",
        "RHipPower",
        "RKneePower",
        "RAnklePower",
    ]
    return {label: point_component_max(acq, label) for label in labels}


def run(config_path, output_dir, input_dir):
    ensure_config(config_path, input_dir)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    input_static_files, input_dynamic_files, _ = copy_trials(input_dir, output_dir)
    static_names = [path.name for path in input_static_files]
    dynamic_names = [path.name for path in input_dynamic_files]
    primary_static = static_names[0]

    total_steps = len(static_names) + len(dynamic_names)
    completed_steps = 0
    emit_progress(completed_steps, total_steps, "Preparing original CGM2.1 workflow")

    data_path = str(output_dir) + "\\"
    log_path = output_dir / "pycgm2-cgm21.log"
    log_path.write_text("", encoding="utf-8")
    pyCGM2.LOGGER.set_file_handler(str(log_path))

    settings = files.loadModelSettings(data_path, "CGM2_1-pyCGM2.settings")
    hjc_method = settings["Calibration"]["HJC"]
    translators = dict(config["translators"])
    filters = config["filters"]
    force_plate_mode = normalize_force_plate_assignment(config.get("forcePlateAssignment", "AUTO"))

    print("Workflow: original pyCGM2 CGM2.1 calibrate/fitting; no kinetic post-processing", flush=True)
    print(f"Force plate assignment input: {config.get('forcePlateAssignment', 'AUTO')} -> {force_plate_mode or 'ORIGINAL_AUTO'}", flush=True)

    emit_progress(completed_steps, total_steps, f"Calibrating static: {primary_static}")
    model, acq_static, static_anomaly = cgm2_1.calibrate(
        data_path,
        primary_static,
        translators,
        config["required_mp"],
        config["optional_mp"],
        bool(config["leftFlatFoot"]),
        bool(config["rightFlatFoot"]),
        bool(config["headFlat"]),
        float(config["markerDiameter"]),
        hjc_method,
        None,
        anomalyException=False,
    )
    btkTools.smartWriter(acq_static, str(output_dir / primary_static))
    completed_steps += 1
    emit_progress(completed_steps, total_steps, f"Completed static: {primary_static}")

    results = [
        {
            "file": primary_static,
            "role": "static",
            "anomaly": bool(static_anomaly),
            "primary": True,
            "workflow": "original-cgm2.1",
        }
    ]

    for extra_static in static_names[1:]:
        emit_progress(completed_steps, total_steps, f"Calibrating additional static: {extra_static}")
        _, extra_acq_static, extra_static_anomaly = cgm2_1.calibrate(
            data_path,
            extra_static,
            dict(config["translators"]),
            config["required_mp"],
            config["optional_mp"],
            bool(config["leftFlatFoot"]),
            bool(config["rightFlatFoot"]),
            bool(config["headFlat"]),
            float(config["markerDiameter"]),
            hjc_method,
            None,
            anomalyException=False,
        )
        btkTools.smartWriter(extra_acq_static, str(output_dir / extra_static))
        completed_steps += 1
        emit_progress(completed_steps, total_steps, f"Completed static: {extra_static}")
        results.append(
            {
                "file": extra_static,
                "role": "static",
                "anomaly": bool(extra_static_anomaly),
                "primary": False,
                "workflow": "original-cgm2.1",
            }
        )

    for trial_name in dynamic_names:
        emit_progress(completed_steps, total_steps, f"Fitting dynamic: {trial_name}")
        if force_plate_mode == "AUTO":
            trial_mfpa = detect_force_plate_assignment(output_dir / trial_name, config["translators"])
        else:
            trial_mfpa = force_plate_mode
        print(f"{trial_name}: force plate assignment passed to fitting -> {trial_mfpa or 'ORIGINAL_AUTO'}", flush=True)
        fitting_kwargs = {"anomalyException": False}
        if bool(config.get("applyFilters", False)):
            fitting_kwargs.update(
                {
                    "fc_lowPass_marker": float(filters["markerCutoffHz"]),
                    "order_lowPass_marker": int(filters["markerOrder"]),
                    "fc_lowPass_forcePlate": float(filters["forcePlateCutoffHz"]),
                    "order_lowPass_forcePlate": int(filters["forcePlateOrder"]),
                }
            )
        acq_gait, gait_anomaly = cgm2_1.fitting(
            model,
            data_path,
            trial_name,
            dict(config["translators"]),
            float(config["markerDiameter"]),
            None,
            trial_mfpa,
            moment_projection(config["momentProjection"]),
            **fitting_kwargs,
        )
        btkTools.smartWriter(acq_gait, str(output_dir / trial_name))
        diagnostics = collect_dynamic_diagnostics(acq_gait)
        print(f"{trial_name}: diagnostics {json.dumps(diagnostics, sort_keys=True)}", flush=True)
        completed_steps += 1
        emit_progress(completed_steps, total_steps, f"Completed dynamic: {trial_name}")
        results.append(
            {
                "file": trial_name,
                "role": "dynamic",
                "anomaly": bool(gait_anomaly),
                "workflow": "original-cgm2.1",
                "forcePlateAssignmentMode": force_plate_mode or "ORIGINAL_AUTO",
                "forcePlateAssignmentPassed": trial_mfpa or "ORIGINAL_AUTO",
                "diagnostics": diagnostics,
            }
        )

    (output_dir / "cgm21_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    emit_progress(total_steps, total_steps, "Processing complete")
    return results


def main():
    parser = argparse.ArgumentParser(description="Run original pyCGM2 CGM2.1 over local C3D trials.")
    parser.add_argument("--input", type=Path, default=APP_ROOT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--init-config", action="store_true")
    args = parser.parse_args()

    input_dir = args.input.resolve()
    config_path = args.config.resolve()
    output_dir = args.output.resolve()

    ensure_config(config_path, input_dir)
    if args.init_config:
        print(f"Config ready: {config_path}")
        return

    results = run(config_path, output_dir, input_dir)
    for result in results:
        print(f"{result['file']}: {result['role']}, anomaly={result['anomaly']}")
    print(f"Processed files written to: {output_dir}")


if __name__ == "__main__":
    main()






