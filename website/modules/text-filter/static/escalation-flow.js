// Maps each action to the level it was first dropped on ("origin" level).
// An action applies to its origin level AND every level above it (cascades up).
const actionStartLevel = {};

const actionLabels = {
    "do-ban": "Ban",
    "do-kick": "Kick",
    "do-delete": "Delete Msg",
    "do-cooldown": "Cooldown",
    "do-mutes": "Mute",
};

const backendKeyToAction = {
    del_msg: "do-delete",
    cooldown: "do-cooldown",
    mute: "do-mutes",
    kick: "do-kick",
    ban: "do-ban",
};

function onChipDragStart(e) {
    e.dataTransfer.setData("text/plain", e.currentTarget.dataset.action);
}

function createPlacedChip(action, isOrigin) {
    const chip = document.createElement("div");
    chip.className = "escalation-chip" + (isOrigin ? "" : " inherited");
    chip.draggable = true;
    chip.dataset.action = action;
    chip.addEventListener("dragstart", onChipDragStart);

    const label = document.createElement("span");
    label.textContent = actionLabels[action];
    chip.appendChild(label);

    if (isOrigin) {
        const remove = document.createElement("span");
        remove.className = "chip-remove";
        remove.textContent = "\u00d7";
        remove.addEventListener("click", (e) => {
            e.stopPropagation();
            delete actionStartLevel[action];
            render();
        });
        chip.appendChild(remove);
    }

    return chip;
}

function render() {
    document.querySelectorAll(".escalation-level-dropzone").forEach((dz) => {
        dz.innerHTML = "";
        const level = parseInt(dz.dataset.level, 10);
        Object.keys(actionStartLevel).forEach((action) => {
            if (actionStartLevel[action] <= level) {
                dz.appendChild(createPlacedChip(action, actionStartLevel[action] === level));
            }
        });
    });

    document.querySelectorAll("#escalation-palette .escalation-chip").forEach((chip) => {
        chip.classList.toggle("placed", chip.dataset.action in actionStartLevel);
    });
}

function getEscalationConfig() {
    const config = { 1: [], 2: [], 3: [], 4: [] };
    for (let level = 1; level <= 4; level++) {
        Object.keys(actionStartLevel).forEach((action) => {
            if (actionStartLevel[action] <= level) {
                config[level].push(action);
            }
        });
    }
    return config;
}
window.getEscalationConfig = getEscalationConfig;

async function saveEscalationConfig() {
    const btn = document.getElementById("escalation-save-btn");
    const status = document.getElementById("escalation-save-status");
    btn.disabled = true;
    status.classList.remove("error");
    status.textContent = "Saving...";

    try {
        const response = await fetch(`/api/text-filter/${guild_id}/set-escalation`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(actionStartLevel),
        });

        if (!response.ok) {
            throw new Error(`Server responded with ${response.status}`);
        }

        status.textContent = "Saved";
    } catch (err) {
        status.classList.add("error");
        status.textContent = "Failed to save";
    } finally {
        btn.disabled = false;
    }
}

function loadSavedEscalationSettings() {
    const dataEl = document.getElementById("escalation-settings-data");
    if (!dataEl || !dataEl.textContent.trim()) return;

    let escalationSettings;
    try {
        escalationSettings = JSON.parse(dataEl.textContent);
    } catch (err) {
        console.error("Failed to parse escalation settings:", err);
        return;
    }

    Object.keys(backendKeyToAction).forEach((backendKey) => {
        const level = escalationSettings[backendKey];
        if (level !== null && level !== undefined) {
            actionStartLevel[backendKeyToAction[backendKey]] = level;
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    loadSavedEscalationSettings();
    render();

    document.querySelectorAll("#escalation-palette .escalation-chip").forEach((chip) => {
        chip.addEventListener("dragstart", onChipDragStart);
    });

    document.querySelectorAll(".escalation-level-dropzone").forEach((dz) => {
        dz.addEventListener("dragover", (e) => {
            e.preventDefault();
            dz.classList.add("drag-over");
        });
        dz.addEventListener("dragleave", () => dz.classList.remove("drag-over"));
        dz.addEventListener("drop", (e) => {
            e.preventDefault();
            dz.classList.remove("drag-over");
            const action = e.dataTransfer.getData("text/plain");
            if (!action) return;
            actionStartLevel[action] = parseInt(dz.dataset.level, 10);
            render();
        });
    });

    const palette = document.getElementById("escalation-palette");
    palette.addEventListener("dragover", (e) => e.preventDefault());
    palette.addEventListener("drop", (e) => {
        e.preventDefault();
        const action = e.dataTransfer.getData("text/plain");
        if (!action) return;
        delete actionStartLevel[action];
        render();
    });

    document.getElementById("escalation-save-btn").addEventListener("click", saveEscalationConfig);
});