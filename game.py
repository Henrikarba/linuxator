"""Bayesian question selection for the distro guessing game."""

import csv
import math
import random
from pathlib import Path

DATASET = Path(__file__).with_name("dataset.csv")
CONFIDENCE_TARGET = 0.93
MIN_QUESTIONS = 20
MAX_QUESTIONS = 40
UNKNOWN_THRESHOLD = 0.60
METADATA = {
    "base_family": "Is it in the {value} family?",
    "release_model": "Does it follow a {value} release model?",
    "primary_package_manager": "Is {value} its main package manager?",
    "default_desktop_name": "Is {value} its default desktop?",
    "default_init": "Does it use {value} as its init system?",
}
NON_QUESTION_COLUMNS = set(METADATA) | {"project_website", "data_quality", "as_of_date"}


def load_dataset(path=DATASET):
    with open(path, newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or reader.fieldnames[0] != "distro":
            raise ValueError("CSV must begin with a distro column")
        rows = list(reader)
        numeric_columns = [key for key in reader.fieldnames[1:] if key not in NON_QUESTION_COLUMNS]
        questions = [key for key in numeric_columns if any(row.get(key, "").strip() for row in rows)]
        metadata_questions = {}
        for column in METADATA:
            if column not in reader.fieldnames:
                continue
            values = {row[column].strip() for row in rows if row[column].strip()}
            for value in sorted(values):
                if len(values) > 1 and value.lower() not in ("none", "unknown", "other", "n/a"):
                    metadata_questions[f"{column}={value}"] = METADATA[column].format(value=value)
        questions.extend(metadata_questions)
        distros = []
        for row in rows:
            name = row["distro"].strip()
            if not name:
                raise ValueError("A distro has no name")
            weights = {q: float(row[q]) if row[q].strip() else 0.5 for q in numeric_columns if q in questions}
            for question in metadata_questions:
                column, value = question.split("=", 1)
                actual = row[column].strip()
                weights[question] = 0.5 if not actual else float(actual == value)
            if any(not math.isfinite(p) or not 0 <= p <= 1 for p in weights.values()):
                raise ValueError(f"Invalid weight for {name}")
            distros.append((name, weights))
    if not distros or len({name for name, _ in distros}) != len(distros):
        raise ValueError("Dataset needs unique distro names")
    return questions, distros, metadata_questions


QUESTIONS, DISTROS, METADATA_QUESTIONS = load_dataset()

QUESTION_TEXT = {
    "rolling_release": "Do you want updates to arrive continuously instead of in big releases?",
    "fixed_release": "Do you prefer predictable, numbered releases?",
    "based_on_debian": "Is it part of the Debian or Ubuntu family?",
    "based_on_arch": "Is it part of the Arch family?",
    "based_on_rhel": "Is it related to Fedora or Red Hat?",
    "independent_base": "Does it have its own independent base?",
    "uses_systemd": "Does it use systemd?",
    "uses_apt": "Do you install software with apt?",
    "uses_pacman": "Do you install software with pacman?",
    "uses_rpm": "Does it use RPM packages?",
    "gnome_default": "Is GNOME its usual desktop?",
    "kde_default": "Is KDE Plasma its usual desktop?",
    "xfce_default": "Is Xfce its usual desktop?",
    "no_default_desktop": "Does it start with no desktop installed?",
    "lightweight_low_resource": "Would it feel at home on a low powered computer?",
    "beginner_friendly": "Would you recommend it to someone new to Linux?",
    "security_privacy_focused": "Is privacy or security a main reason to use it?",
    "gaming_focused": "Does gaming play a central role in its identity?",
    "server_enterprise_focused": "Is it built mainly for servers or enterprise use?",
    "immutable_filesystem": "Is its system designed to be immutable or atomic?",
    "commercial_backing": "Is there a company behind it?",
    "gui_installer_friendly": "Would a friendly graphical installer greet you?",
    "terminal_first_experience": "Are you expected to spend a lot of time in a terminal?",
    "released_before_2010": "Was it around before 2010?",
    "released_after_2015": "Did it first appear after 2015?",
    "uses_sysvinit_or_openrc_or_runit": "Does it avoid systemd for its init system?",
    "minimalist_by_design": "Does it take a minimalist approach?",
    "developer_focused": "Does it especially appeal to developers?",
    "good_for_old_hardware": "Could it give an old laptop a second life?",
    "suitable_for_servers_no_gui": "Would it be comfortable running a server without a GUI?",
    "ubuntu_family": "Is it an Ubuntu edition or a distro built directly on Ubuntu?",
    "made_for_gaming_handhelds": "Would you expect to find it on a gaming handheld?",
    "declarative_configuration": "Can you describe your whole system in a configuration file?",
    "privacy_live_session": "Would you boot it from a USB stick for a private session?",
    "upstream_of_ubuntu": "Is it the upstream project that Ubuntu is built from?",
    "cinnamon_desktop": "Is Cinnamon its signature desktop?",
    "pantheon_desktop": "Is Pantheon its signature desktop?",
    "windows_like_desktop": "Is its desktop designed to feel familiar to Windows users?",
    "centos_stream_model": "Does it track just ahead of Red Hat Enterprise Linux?",
    "rocky_enterprise_clone": "Is its name a tribute to CentOS cofounder Rocky McGaugh?",
    "almalinux_enterprise_clone": "Was it originally launched by CloudLinux?",
    "ubuntu_xfce_flavor": "Is it the official Ubuntu flavor centered on Xfce?",
    "ubuntu_mate_flavor": "Is it the official Ubuntu flavor centered on MATE?",
    "mandriva_descendant": "Does it descend from Mandriva Linux?",
    "feren_kde_desktop": "Does it combine an Ubuntu base with a customized KDE desktop?",
}


def label(key):
    if key in METADATA_QUESTIONS:
        return METADATA_QUESTIONS[key]
    if key in QUESTION_TEXT:
        return QUESTION_TEXT[key]
    return key.replace("_", " ").capitalize() + "?"


def entropy(probabilities):
    return -sum(p * math.log2(p) for p in probabilities if p > 0)


def state(answers):
    if not isinstance(answers, list) or len(answers) > MAX_QUESTIONS:
        raise ValueError("Invalid answer history")
    seen = set()
    for item in answers:
        if not isinstance(item, dict) or item.get("question") not in QUESTIONS or item.get("answer") not in ("yes", "no", "unknown"):
            raise ValueError("Invalid answer")
        if item["question"] in seen:
            raise ValueError("A question was answered twice")
        seen.add(item["question"])

    # Log space avoids underflow after many answers. A small floor allows recovery
    # from one unexpected answer even when the source data says 0 or 1.
    scores = []
    for _, weights in DISTROS:
        score = 0.0
        for item in answers:
            if item["answer"] == "unknown":
                continue
            p = min(0.99, max(0.01, weights[item["question"]]))
            score += math.log(p if item["answer"] == "yes" else 1 - p)
        scores.append(score)
    scale = max(scores)
    raw = [math.exp(s - scale) for s in scores]
    total = sum(raw)
    posterior = [p / total for p in raw]
    ranking = sorted(zip((name for name, _ in DISTROS), posterior), key=lambda pair: pair[1], reverse=True)
    leader, confidence = ranking[0]

    result = {
        "count": len(answers),
        "total_distros": len(DISTROS),
        "confidence": round(confidence, 4),
        "leader": leader,
        "top": [{"name": name, "probability": round(p, 4)} for name, p in ranking[:3]],
    }
    certain = confidence > CONFIDENCE_TARGET
    if (len(answers) >= MIN_QUESTIONS and certain) or len(answers) >= MAX_QUESTIONS:
        result.update(done=True, certain=certain, unknown=confidence < UNKNOWN_THRESHOLD)
        return result

    current_entropy = entropy(posterior)
    candidates = []
    for question in QUESTIONS:
        if question in seen:
            continue
        likelihoods = [min(0.99, max(0.01, weights[question])) for _, weights in DISTROS]
        yes_probability = sum(p * likelihood for p, likelihood in zip(posterior, likelihoods))
        yes_posterior = [p * likelihood / yes_probability for p, likelihood in zip(posterior, likelihoods)]
        no_posterior = [p * (1 - likelihood) / (1 - yes_probability) for p, likelihood in zip(posterior, likelihoods)]
        gain = current_entropy - yes_probability * entropy(yes_posterior) - (1 - yes_probability) * entropy(no_posterior)
        # Tiny preference for playful questions when they are nearly as useful.
        score = gain + (0.012 if question.startswith(("would_", "do_you_")) else 0)
        candidates.append((score, question))
    candidates.sort(reverse=True)
    # Randomize among the strongest questions, preserving useful information gain.
    question = random.choice(candidates[:5])[1]
    result.update(done=False, question={"id": question, "text": label(question)})
    return result
