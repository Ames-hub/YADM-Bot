document.addEventListener("DOMContentLoaded", async () => {
    console.log("Toggle script loaded");

    const buttons = document.querySelectorAll("#toggle-buttons .toggle-btn");
    const mainButton = document.querySelector("#main-module-button");

    const moduleMap = {
        "text-filter": "text-filter",
        "spam-filter": "spam-filter",
        "image-filter": "img-filter"
    };

    const moduleName =
        moduleMap[window.location.pathname.split("/").filter(Boolean).pop()];

    console.log("Found buttons:", buttons.length);
    console.log("Main module:", moduleName);

    function setButtonState(button, isActive) {
        button.classList.toggle("active", isActive);
        button.textContent = isActive ? "ON" : "OFF";
    }

    async function toggleModule(button, moduleName) {
        const isActive = !button.classList.contains("active");

        setButtonState(button, isActive);

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

            console.log(`Module "${moduleName}" set to ${isActive}`);

        } catch (error) {
            console.error(
                `Failed to toggle module "${moduleName}":`,
                error
            );

            // Revert the button if the API request failed
            setButtonState(button, !isActive);
        }
    }

    // Get the current module states
    try {
        const response = await fetch(`/api/guild/${guild_id}/modules`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const modules = await response.json();

        // Set individual module buttons
        buttons.forEach((btn) => {
            const buttonModuleName = btn.id.replace("toggle-", "");
            const isActive = modules[buttonModuleName] ?? false;

            setButtonState(btn, isActive);
        });

        // Set main module button
        if (mainButton && moduleName) {
            const isActive = modules[moduleName] ?? false;

            setButtonState(mainButton, isActive);
        }

    } catch (error) {
        console.error("Failed to load module states:", error);
    }

    // Handle individual module buttons
    buttons.forEach((btn) => {
        btn.addEventListener("click", () => {
            const buttonModuleName = btn.id.replace("toggle-", "");

            btn.disabled = true;
            toggleModule(btn, buttonModuleName);
            btn.enabled = true;
        });
    });

    // Handle main module button
    if (mainButton && moduleName) {
        mainButton.addEventListener("click", () => {
            toggleModule(mainButton, moduleName);
        });
    }
});