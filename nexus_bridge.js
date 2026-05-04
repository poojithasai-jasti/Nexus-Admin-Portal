const nexusBridge = {
    async login() {
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const status = document.getElementById('status');

        status.innerText = "Connecting to Nexus Engine...";

        try {
            const response = await fetch('http://127.0.0.1:8080/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();

            if (response.ok) {
                status.innerText = "Access Granted. Redirecting...";
                status.style.color = "#4ecca3";
                // Add redirect logic here later
            } else {
                status.innerText = "Error: " + data.error;
                status.style.color = "#ff4d4d";
            }
        } catch (error) {
            status.innerText = "Nexus Engine Offline. Start app.py first!";
            status.style.color = "#ff4d4d";
        }
    }
};
