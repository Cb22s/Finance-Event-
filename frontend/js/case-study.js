document.addEventListener('DOMContentLoaded', async () => {
    const waitForSession = async () => {
        let retries = 5;
        while (retries--) {
            const { data: { session } } = await window.supabase.auth.getSession();
            if (session) {
                console.log("Session READY:", session);
                return session;
            }
            console.log("Waiting for session...");
            await new Promise(res => setTimeout(res, 500));
        }
        console.log("No session after retries → redirect");
        alert("Unauthorized - Please Login First");
        window.location.href = '/';
        return null;
    };

    const session = await waitForSession();
    if (!session) return;


    // Auth state update
    window.supabase.auth.onAuthStateChange((event, session) => {
        if (!session) window.location.href = '/';
    });


    // Fetch case study
    try {
        const h = { 'Authorization': `Bearer ${session.access_token}` };
        const response = await fetch(`${API_BASE_URL}/case-study`, { headers: h });

        const data = await response.json();
        
        document.getElementById('csTitle').innerText = data.title || "The First Job";
        document.getElementById('csDesc').innerText = data.description || "You have landed your first job...";
        const living = data.lifestyles.city;
        document.getElementById('csRent').innerText = `₹${living.rent.toLocaleString('en-IN')}`;
        document.getElementById('csFood').innerText = `₹${living.food.toLocaleString('en-IN')}`;
        document.getElementById('csTransport').innerText = `₹${living.transport.toLocaleString('en-IN')}`;
        document.getElementById('csFamily').innerText = `₹${living.utilities.toLocaleString('en-IN')}`;
    } catch (err) {
        console.error('Error fetching case study:', err);
    }
});

