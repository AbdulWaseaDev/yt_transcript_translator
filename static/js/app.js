let fetchedTranscript = "";
let detectedLang = "";

document.getElementById("fetch-btn").addEventListener("click", async function () {
    const videoUrl = document.getElementById("video-url").value.trim();
    if (!videoUrl) {
        document.getElementById("url-error").textContent = "Please enter a YouTube URL";
        return;
    }
    document.getElementById("url-error").textContent = "";
    showLoading(true);

    try {
        const res = await fetch("/fetch_transcript", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ video_url: videoUrl })
        });
        const data = await res.json();

        if (res.ok) {
            fetchedTranscript = data.transcript;
            detectedLang = data.source_lang;
            document.getElementById("original-transcript").textContent = fetchedTranscript;
            document.getElementById("preserve-terms").value = data.suggested_terms.join(", ");
            document.getElementById("results").style.display = "flex";
            document.getElementById("translate-btn").disabled = false;
        } else {
            document.getElementById("url-error").textContent = data.error || "Failed to fetch transcript";
        }
    } catch (err) {
        document.getElementById("url-error").textContent = "Error connecting to server";
    }
    showLoading(false);
});

document.getElementById("translate-btn").addEventListener("click", async function () {
    const targetLang = document.getElementById("target-language").value;
    const preserveTerms = document.getElementById("preserve-terms").value
        .split(",")
        .map(t => t.trim())
        .filter(t => t.length > 0);

    showLoading(true);

    try {
        const res = await fetch("/translate_transcript", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                transcript: fetchedTranscript,
                source_lang: detectedLang,
                target_lang: targetLang,
                preserve_terms: preserveTerms
            })
        });
        const data = await res.json();

        if (res.ok) {
            document.getElementById("translated-transcript").textContent = data.translated;
        } else {
            alert(data.error || "Translation failed");
        }
    } catch (err) {
        alert("Error connecting to server");
    }
    showLoading(false);
});

function showLoading(isLoading) {
    document.getElementById("loading").style.display = isLoading ? "block" : "none";
}
