function copyToClipboard(text, elementId) {
    navigator.clipboard.writeText(text).then(function() {
        const btn = document.getElementById(elementId);
        if (btn) {
            const originalText = btn.innerText;
            btn.innerText = "Copiado!";
            btn.style.backgroundColor = "#10b981";
            btn.style.color = "#fff";
            setTimeout(() => {
                btn.innerText = originalText;
                btn.style.backgroundColor = "";
                btn.style.color = "";
            }, 2000);
        }
    }).catch(function(err) {
        console.error("Erro ao copiar para clipboard: ", err);
    });
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = "none";
    }
}

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = "flex";
    }
}
