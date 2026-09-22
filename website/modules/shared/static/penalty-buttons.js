// Escalation flow must always be loaded before this script, so that one will handle finding "PENALTY_MODULE" and all that.

document.addEventListener("DOMContentLoaded", async () => {
    const buttons = document.querySelectorAll("#actions .toggle-btn");

    // Load current toggle states
    try {
        const response = await fetch(`/api/guild/${guild_id}/modules/get-penalty/${PENALTY_MODULE}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const states = await response.json();

        buttons.forEach((btn) => {
            const toggleName = btn.id.replace("toggle-", "");
            const isActive = states[toggleName] ?? false;

            btn.classList.toggle("active", isActive);
            btn.textContent = isActive ? "ON" : "OFF";
        });
    } catch (error) {
        console.error("Failed to load penalty toggle states:", error);
    }

    // Handle button clicks
    buttons.forEach((btn) => {
        btn.addEventListener("click", async () => {
            const isActive = btn.classList.toggle("active");
            btn.textContent = isActive ? "ON" : "OFF";

            const toggleName = btn.id.replace("toggle-", "");

            try {
                const response = await fetch(
                    `/api/guild/${guild_id}/modules/set-penalty/${PENALTY_MODULE}`,
                    {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ [toggleName]: isActive }),
                    }
                );

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                syncEscalationWithPenalties();
            } catch (error) {
                console.error(`Failed to toggle "${toggleName}":`, error);

                // Revert the button if the API request failed
                btn.classList.toggle("active");
                btn.textContent = isActive ? "OFF" : "ON";
            }
        });
    });

    syncEscalationWithPenalties();
});