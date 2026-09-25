document.addEventListener("DOMContentLoaded", () => {
    const durationInputs = document.querySelectorAll(".duration-input");
    const debounceTimers = {};

    durationInputs.forEach(input => {
        input.addEventListener("input", () => {
            const durationName = input.id;

            // Cancel the previous pending request for this input
            clearTimeout(debounceTimers[durationName]);

            // Wait 500ms after the user stops typing
            debounceTimers[durationName] = setTimeout(async () => {
                try {
                    const response = await fetch(
                        `/api/guild/${guild_id}/${PENALTY_MODULE}/durations/${durationName}`,
                        {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json"
                            },
                            body: JSON.stringify({
                                value: Number(input.value)
                            })
                        }
                    );

                    if (!response.ok) {
                        console.error(
                            `Failed to update ${durationName}:`,
                            response.status,
                            await response.text()
                        );
                    }
                } catch (error) {
                    console.error(`Failed to update ${durationName}:`, error);
                }
            }, 500);
        });
    });
});