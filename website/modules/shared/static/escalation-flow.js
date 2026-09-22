const module_map = {
    "text-filter": "text",
    "spam-filter": "spam",
    "image-filter": "image"
};

const moduleName = window.location.pathname.split("/").filter(Boolean).pop();
const PENALTY_MODULE = module_map[moduleName];

if (!PENALTY_MODULE) {
    throw new Error(`Unknown module: ${moduleName}`);
}

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
    const action = e.currentTarget.dataset.action;
    const button = document.getElementById(`toggle-${action}`);

    if (!button?.classList.contains("active")) {
        e.preventDefault();
        return;
    }

    e.dataTransfer.setData("text/plain", action);
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

function syncEscalationWithPenalties() {
    Object.keys(actionLabels).forEach((action) => {
        const button = document.getElementById(`toggle-${action}`);
        const chip = document.querySelector(
            `#escalation-palette .escalation-chip[data-action="${action}"]`
        );

        if (!button || !chip) return;

        const isActive = button.classList.contains("active");

        // Disable/enable the palette chip.
        chip.draggable = isActive;
        chip.classList.toggle("disabled", !isActive);

        // If the penalty is disabled, remove it from every escalation level.
        if (!isActive) {
            delete actionStartLevel[action];
        }
    });

    // Rebuild the escalation levels and palette state.
    render();
}

function render() {
    document.querySelectorAll(".escalation-level-dropzone").forEach((dz) => {
        dz.innerHTML = "";
        const level = parseInt(dz.dataset.level, 10);

        Object.keys(actionStartLevel).forEach((action) => {
            if (actionStartLevel[action] <= level) {
                dz.appendChild(
                    createPlacedChip(
                        action,
                        actionStartLevel[action] === level
                    )
                );
            }
        });
    });

    document.querySelectorAll("#escalation-palette .escalation-chip").forEach((chip) => {
        const action = chip.dataset.action;
        const button = document.getElementById(`toggle-${action}`);
        const isActive = button?.classList.contains("active") ?? false;

        chip.classList.toggle("placed", action in actionStartLevel);
        chip.classList.toggle("disabled", !isActive);
        chip.draggable = isActive;
        chip.title = isActive ? "" : "This penalty is disabled! Enable it to be able to put in the escalation flow.";
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
        // Include every action, using null for unselected actions.
        const config = {};

        Object.keys(actionLabels).forEach((action) => {
            config[action] = actionStartLevel[action] ?? null;
        });

        const response = await fetch(
            `/api/${moduleName}/${guild_id}/set-escalation`,
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(config),
            }
        );

        if (!response.ok) {
            throw new Error(`Server responded with ${response.status}`);
        }

        // Keep the penalty buttons in sync with the escalation settings.
        Object.keys(actionLabels).forEach((action) => {
            const button = document.getElementById(`toggle-${action}`);
            if (!button) return;

            const isActive = config[action] !== null;

            button.classList.toggle("active", isActive);
            button.textContent = isActive ? "ON" : "OFF";
        });

        // Re-sync the escalation chips after updating the buttons.
        syncEscalationWithPenalties();

        status.textContent = "Saved";
    } catch (err) {
        console.error("Failed to save escalation config:", err);
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

    document
        .querySelectorAll("#escalation-palette .escalation-chip")
        .forEach((chip) => {
            chip.addEventListener("dragstart", onChipDragStart);
        });

    document
        .querySelectorAll(".escalation-level-dropzone")
        .forEach((dz) => {
            dz.addEventListener("dragover", (e) => {
                e.preventDefault();
                dz.classList.add("drag-over");
            });

            dz.addEventListener("dragleave", () => {
                dz.classList.remove("drag-over");
            });

            dz.addEventListener("drop", (e) => {
                e.preventDefault();
                dz.classList.remove("drag-over");

                const action = e.dataTransfer.getData("text/plain");
                if (!action) return;

                // Don't allow disabled penalties to be placed.
                const button = document.getElementById(`toggle-${action}`);
                if (!button?.classList.contains("active")) return;

                actionStartLevel[action] = parseInt(dz.dataset.level, 10);
                render();
            });
        });

    const palette = document.getElementById("escalation-palette");

    palette.addEventListener("dragover", (e) => {
        e.preventDefault();
    });

    palette.addEventListener("drop", (e) => {
        e.preventDefault();

        const action = e.dataTransfer.getData("text/plain");
        if (!action) return;

        delete actionStartLevel[action];
        render();
    });

    document
        .getElementById("escalation-save-btn")
        .addEventListener("click", saveEscalationConfig);
});