document.addEventListener("DOMContentLoaded", async () => {
    console.log("Toggle script loaded");

    const buttons = document.querySelectorAll("#toggle-buttons .toggle-btn");

    console.log("Found buttons:", buttons.length);

    // Get the current module states
    try {
        const response = await fetch(`/api/guild/${guild_id}/modules`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const modules = await response.json();

        // Set each button to its actual state
        buttons.forEach((btn) => {
            const moduleName = btn.id.replace("toggle-", "");
            const isActive = modules[moduleName] ?? false;

            btn.classList.toggle("active", isActive);
            btn.textContent = isActive ? "ON" : "OFF";
            console.log(moduleName)
            if (['text-filter', 'spam-filter', 'image-filter'].includes(moduleName)) {
                console.log(`Looking for ${moduleName}-strong to set strong elements colour`)
                strong_element = document.getElementById(`${moduleName.replace("toggle-", "")}-strong`)
                strong_element.style.color = !isActive ? "#e74c3c" : "#9099e9"
            }
            else {
                console.log(`Skipped Looking for ${moduleName}, no strong element to set colour for.`)
            }
        });

    } catch (error) {
        console.error("Failed to load module states:", error);
    }

    // Handle button clicks
    buttons.forEach((btn) => {
        btn.addEventListener("click", async () => {
            console.log("Clicked:", btn.id);

            const isActive = btn.classList.toggle("active");
            btn.textContent = isActive ? "ON" : "OFF";

            const moduleName = btn.id.replace("toggle-", "");

            try {
                const response = await fetch(
                    `/api/guild/${guild_id}/modules/toggle/${moduleName}/${isActive}`,
                    {
                        method: "POST"
                    }
                );

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                if (['text-filter', 'spam-filter', 'image-filter'].includes(moduleName)) {
                    console.log(`Looking for ${moduleName}-strong to set strong elements colour`)
                    strong_element = document.getElementById(`${moduleName}-strong`)
                    strong_element.textContent = !isActive ? "Offline" : "Online"
                    strong_element.style.color = !isActive ? "#e74c3c" : "#9099e9"
                }

                console.log(
                    `Module "${moduleName}" set to ${isActive}`
                );

            } catch (error) {
                console.error("Failed to toggle module:", error);

                // Revert the button if the API request failed
                btn.classList.toggle("active");
                btn.textContent = isActive ? "OFF" : "ON";
            }
        });
    });
});