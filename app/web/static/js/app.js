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

// Sidebar Smooth Collapse Controller
document.addEventListener("DOMContentLoaded", function () {
    const sidebar = document.querySelector(".sidebar");
    const mainWrapper = document.querySelector(".main-wrapper");
    const toggleBtn = document.getElementById("sidebarToggle");

    if (sidebar && toggleBtn) {
        // Restaurar estado salvo no navegador
        const isCollapsed = localStorage.getItem("focus_sidebar_collapsed") === "true";
        if (isCollapsed) {
            sidebar.classList.add("collapsed");
            if (mainWrapper) mainWrapper.classList.add("collapsed");
        }

        toggleBtn.addEventListener("click", function () {
            sidebar.classList.toggle("collapsed");
            if (mainWrapper) mainWrapper.classList.toggle("collapsed");
            localStorage.setItem(
                "focus_sidebar_collapsed",
                sidebar.classList.contains("collapsed")
            );
        });
    }

    // ==========================================
    // CONTROLE DA SIDEBAR RESPONSIVA (MOBILE DRAWER)
    // ==========================================
    const mobileMenuBtn = document.getElementById("mobileMenuBtn");
    const sidebarBackdrop = document.getElementById("sidebarBackdrop");
    const btnSidebarMobileClose = document.getElementById("btnSidebarMobileClose");

    function openMobileSidebar() {
        if (sidebar) sidebar.classList.add("mobile-open");
        if (sidebarBackdrop) sidebarBackdrop.classList.add("show");
        document.body.style.overflow = "hidden";
    }

    function closeMobileSidebar() {
        if (sidebar) sidebar.classList.remove("mobile-open");
        if (sidebarBackdrop) sidebarBackdrop.classList.remove("show");
        document.body.style.overflow = "";
    }

    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener("click", function (e) {
            e.stopPropagation();
            if (sidebar && sidebar.classList.contains("mobile-open")) {
                closeMobileSidebar();
            } else {
                openMobileSidebar();
            }
        });
    }

    if (sidebarBackdrop) {
        sidebarBackdrop.addEventListener("click", closeMobileSidebar);
    }

    if (btnSidebarMobileClose) {
        btnSidebarMobileClose.addEventListener("click", closeMobileSidebar);
    }

    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && sidebar && sidebar.classList.contains("mobile-open")) {
            closeMobileSidebar();
        }
    });

    // ==========================================
    // CONTROLE DO MÓDULO INÍCIO
    // ==========================================

    // Popover de Módulos (Grid 9 dots)
    const modulesToggleBtn = document.getElementById("modulesToggleBtn");
    const modulesPopover = document.getElementById("modulesPopover");
    if (modulesToggleBtn && modulesPopover) {
        modulesToggleBtn.addEventListener("click", function (e) {
            e.stopPropagation();
            const isOpen = modulesPopover.classList.toggle("show");
            modulesToggleBtn.setAttribute("aria-expanded", isOpen);
            if (notificationsDropdown) notificationsDropdown.classList.remove("show");
            if (profileMenuDropdown) profileMenuDropdown.classList.remove("show");
        });
    }

    // Dropdown de Notificações
    const notificationsToggleBtn = document.getElementById("notificationsToggleBtn");
    const notificationsDropdown = document.getElementById("notificationsDropdown");
    if (notificationsToggleBtn && notificationsDropdown) {
        notificationsToggleBtn.addEventListener("click", function (e) {
            e.stopPropagation();
            const isOpen = notificationsDropdown.classList.toggle("show");
            notificationsToggleBtn.setAttribute("aria-expanded", isOpen);
            if (modulesPopover) modulesPopover.classList.remove("show");
            if (profileMenuDropdown) profileMenuDropdown.classList.remove("show");
        });
    }

    // Dropdown de Perfil
    const profileToggleBtn = document.getElementById("profileToggleBtn");
    const profileMenuDropdown = document.getElementById("profileMenuDropdown");
    if (profileToggleBtn && profileMenuDropdown) {
        profileToggleBtn.addEventListener("click", function (e) {
            e.stopPropagation();
            const isOpen = profileMenuDropdown.classList.toggle("show");
            profileToggleBtn.setAttribute("aria-expanded", isOpen);
            if (modulesPopover) modulesPopover.classList.remove("show");
            if (notificationsDropdown) notificationsDropdown.classList.remove("show");
        });
    }

    // Fechar dropdowns ao clicar fora
    document.addEventListener("click", function (e) {
        if (modulesPopover && !modulesPopover.contains(e.target) && e.target !== modulesToggleBtn) {
            modulesPopover.classList.remove("show");
            if (modulesToggleBtn) modulesToggleBtn.setAttribute("aria-expanded", "false");
        }
        if (notificationsDropdown && !notificationsDropdown.contains(e.target) && e.target !== notificationsToggleBtn) {
            notificationsDropdown.classList.remove("show");
            if (notificationsToggleBtn) notificationsToggleBtn.setAttribute("aria-expanded", "false");
        }
        if (profileMenuDropdown && !profileMenuDropdown.contains(e.target) && e.target !== profileToggleBtn) {
            profileMenuDropdown.classList.remove("show");
            if (profileToggleBtn) profileMenuDropdown.setAttribute("aria-expanded", "false");
        }
    });

    // Modais do Início
    const modalDrive = document.getElementById("modalDrive");
    const modalUpload = document.getElementById("modalUpload");
    const btnShortcutDrive = document.getElementById("btnShortcutDrive");
    const btnShortcutUpload = document.getElementById("btnShortcutUpload");
    const btnEmptyUpload = document.getElementById("btnEmptyUpload");
    const btnCloseModalDrive = document.getElementById("btnCloseModalDrive");
    const btnCloseModalUpload = document.getElementById("btnCloseModalUpload");
    const btnCancelUpload = document.getElementById("btnCancelUpload");

    function openModalBackdrop(modal) {
        if (modal) {
            modal.classList.add("show");
            document.body.style.overflow = "hidden";
        }
    }

    function closeModalBackdrop(modal) {
        if (modal) {
            modal.classList.remove("show");
            document.body.style.overflow = "";
        }
    }

    if (btnShortcutDrive) {
        btnShortcutDrive.addEventListener("click", () => openModalBackdrop(modalDrive));
    }
    if (btnCloseModalDrive) {
        btnCloseModalDrive.addEventListener("click", () => closeModalBackdrop(modalDrive));
    }

    if (btnShortcutUpload) {
        btnShortcutUpload.addEventListener("click", () => openModalBackdrop(modalUpload));
    }
    if (btnEmptyUpload) {
        btnEmptyUpload.addEventListener("click", () => openModalBackdrop(modalUpload));
    }
    if (btnCloseModalUpload) {
        btnCloseModalUpload.addEventListener("click", () => closeModalBackdrop(modalUpload));
    }
    if (btnCancelUpload) {
        btnCancelUpload.addEventListener("click", () => closeModalBackdrop(modalUpload));
    }

    // Fechar ao clicar no backdrop escuro
    [modalDrive, modalUpload].forEach(modal => {
        if (modal) {
            modal.addEventListener("click", function (e) {
                if (e.target === modal) {
                    closeModalBackdrop(modal);
                }
            });
        }
    });

    // Tecla Escape fecha modais e dropdowns
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") {
            closeModalBackdrop(modalDrive);
            closeModalBackdrop(modalUpload);
            if (modulesPopover) modulesPopover.classList.remove("show");
            if (notificationsDropdown) notificationsDropdown.classList.remove("show");
            if (profileMenuDropdown) profileMenuDropdown.classList.remove("show");
            
            const searchInput = document.getElementById("unifiedSearchInput");
            if (searchInput) {
                searchInput.value = "";
                filterProjects("");
                searchInput.blur();
                if (searchBoxWrapper) searchBoxWrapper.classList.remove("expanded");
            }
        }
    });

    // Drag & Drop no Upload de Vídeo
    const dropzoneArea = document.getElementById("dropzoneArea");
    const videoFileInput = document.getElementById("videoFileInput");
    const selectedFileName = document.getElementById("selectedFileName");
    const btnSubmitUpload = document.getElementById("btnSubmitUpload");

    if (dropzoneArea && videoFileInput) {
        ["dragenter", "dragover"].forEach(eventName => {
            dropzoneArea.addEventListener(eventName, function (e) {
                e.preventDefault();
                dropzoneArea.classList.add("drag-over");
            }, false);
        });

        ["dragleave", "drop"].forEach(eventName => {
            dropzoneArea.addEventListener(eventName, function (e) {
                e.preventDefault();
                dropzoneArea.classList.remove("drag-over");
            }, false);
        });

        dropzoneArea.addEventListener("drop", function (e) {
            const files = e.dataTransfer.files;
            if (files && files.length > 0) {
                videoFileInput.files = files;
                handleFileSelected(files[0]);
            }
        });

        videoFileInput.addEventListener("change", function () {
            if (videoFileInput.files && videoFileInput.files.length > 0) {
                handleFileSelected(videoFileInput.files[0]);
            }
        });

        function handleFileSelected(file) {
            if (selectedFileName && btnSubmitUpload) {
                const sizeMb = (file.size / (1024 * 1024)).toFixed(1);
                selectedFileName.textContent = `Arquivo selecionado: ${file.name} (${sizeMb} MB)`;
                btnSubmitUpload.removeAttribute("disabled");
            }
        }
    }

    // ==========================================
    // BUSCA MINIMALISTA EXPANSÍVEL EM TEMPO REAL
    // ==========================================
    const searchBoxWrapper = document.getElementById("searchBoxWrapper");
    const btnSearchTrigger = document.getElementById("btnSearchTrigger");
    const btnSearchClear = document.getElementById("btnSearchClear");
    const unifiedSearchInput = document.getElementById("unifiedSearchInput");

    function filterProjects(query) {
        const q = query.trim().toLowerCase();
        const projectCards = document.querySelectorAll(".project-card");
        let visibleCount = 0;

        projectCards.forEach(card => {
            const title = card.getAttribute("data-title") || "";
            const filename = card.getAttribute("data-filename") || "";
            if (!q || title.includes(q) || filename.includes(q)) {
                card.style.display = "flex";
                visibleCount++;
            } else {
                card.style.display = "none";
            }
        });
    }

    if (btnSearchTrigger && searchBoxWrapper && unifiedSearchInput) {
        btnSearchTrigger.addEventListener("click", function (e) {
            e.stopPropagation();
            if (!searchBoxWrapper.classList.contains("expanded")) {
                searchBoxWrapper.classList.add("expanded");
                unifiedSearchInput.focus();
            }
        });
    }

    if (btnSearchClear && searchBoxWrapper && unifiedSearchInput) {
        btnSearchClear.addEventListener("click", function (e) {
            e.stopPropagation();
            unifiedSearchInput.value = "";
            filterProjects("");
            searchBoxWrapper.classList.remove("expanded");
        });
    }

    if (unifiedSearchInput) {
        unifiedSearchInput.addEventListener("input", function (e) {
            filterProjects(e.target.value);
        });
    }

    // Fechar busca ao clicar fora se estiver vazia
    document.addEventListener("click", function (e) {
        if (searchBoxWrapper && searchBoxWrapper.classList.contains("expanded")) {
            if (!searchBoxWrapper.contains(e.target)) {
                if (unifiedSearchInput && unifiedSearchInput.value.trim() === "") {
                    searchBoxWrapper.classList.remove("expanded");
                }
            }
        }
    });

    // ==========================================
    // REPRODUÇÃO & PRÉ-VISUALIZAÇÃO DE VÍDEO DO DRIVE
    // ==========================================
    const modalVideoPreview = document.getElementById("modalVideoPreview");
    const previewVideoElement = document.getElementById("previewVideoElement");
    const modalVideoPreviewTitle = document.getElementById("modalVideoPreviewTitle");
    const previewMetaResolution = document.getElementById("previewMetaResolution");
    const previewMetaDuration = document.getElementById("previewMetaDuration");
    const previewMetaStatus = document.getElementById("previewMetaStatus");
    const btnPreviewGoReview = document.getElementById("btnPreviewGoReview");
    const btnCloseModalPreview = document.getElementById("btnCloseModalPreview");
    const btnClosePreviewBtn = document.getElementById("btnClosePreviewBtn");

    function stopAndCloseVideoPreview() {
        if (previewVideoElement) {
            previewVideoElement.pause();
            previewVideoElement.removeAttribute("src");
            previewVideoElement.load();
        }
        if (modalVideoPreview) {
            closeModalBackdrop(modalVideoPreview);
        }
    }

    // Ligar todos os botões de pré-visualização (play button e botão assistir)
    document.querySelectorAll(".btn-preview-video").forEach(btn => {
        btn.addEventListener("click", function (e) {
            e.preventDefault();
            e.stopPropagation();

            const videoSrc = this.getAttribute("data-video-src");
            const videoTitle = this.getAttribute("data-video-title") || "Vídeo";
            const videoResolution = this.getAttribute("data-video-resolution") || "1080x1920";
            const videoDuration = this.getAttribute("data-video-duration") || "00:00";
            const videoStatus = this.getAttribute("data-video-status") || "DRAFT";
            const draftId = this.getAttribute("data-draft-id") || "";

            if (modalVideoPreview && previewVideoElement && videoSrc) {
                modalVideoPreviewTitle.textContent = videoTitle;
                if (previewMetaResolution) previewMetaResolution.textContent = videoResolution;
                if (previewMetaDuration) previewMetaDuration.textContent = videoDuration;
                if (previewMetaStatus) {
                    previewMetaStatus.textContent = videoStatus;
                    previewMetaStatus.className = "badge badge-" + videoStatus.toLowerCase();
                }
                if (btnPreviewGoReview && draftId) {
                    btnPreviewGoReview.href = `/review?draft_id=${draftId}`;
                }

                previewVideoElement.src = videoSrc;
                openModalBackdrop(modalVideoPreview);
                previewVideoElement.load();
                previewVideoElement.play().catch(err => {
                    console.warn("Autoplay bloqueado pelo navegador, aguardando clique do usuário:", err);
                });
            }
        });
    });

    if (btnCloseModalPreview) {
        btnCloseModalPreview.addEventListener("click", stopAndCloseVideoPreview);
    }
    if (btnClosePreviewBtn) {
        btnClosePreviewBtn.addEventListener("click", stopAndCloseVideoPreview);
    }

    if (modalVideoPreview) {
        modalVideoPreview.addEventListener("click", function (e) {
            if (e.target === modalVideoPreview) {
                stopAndCloseVideoPreview();
            }
        });
    }

    // Tecla ESC fecha a pré-visualização de vídeo e pausa áudio
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && modalVideoPreview && modalVideoPreview.classList.contains("show")) {
            stopAndCloseVideoPreview();
        }
    });

    // ==========================================
    // CONTROLADOR DE TEMA (MODO WHITE / CLARO)
    // ==========================================
    const themeButtons = document.querySelectorAll(".theme-toggle-btn");

    function updateThemeUI(theme) {
        if (theme === "light") {
            document.documentElement.classList.add("light-theme");
            document.body.classList.add("light-theme");
            themeButtons.forEach(btn => {
                btn.setAttribute("title", "Alternar para Modo Escuro");
                btn.setAttribute("aria-label", "Alternar para Modo Escuro");
                const textSpan = btn.querySelector(".theme-text");
                if (textSpan) textSpan.textContent = "Modo Escuro";
            });
        } else {
            document.documentElement.classList.remove("light-theme");
            document.body.classList.remove("light-theme");
            themeButtons.forEach(btn => {
                btn.setAttribute("title", "Alternar para Modo Claro");
                btn.setAttribute("aria-label", "Alternar para Modo Claro");
                const textSpan = btn.querySelector(".theme-text");
                if (textSpan) textSpan.textContent = "Modo Claro";
            });
        }
    }

    // Inicializar com tema salvo
    const currentTheme = localStorage.getItem("focus_theme") || "dark";
    updateThemeUI(currentTheme);

    themeButtons.forEach(btn => {
        btn.addEventListener("click", function (e) {
            e.stopPropagation();
            const isCurrentlyLight = document.body.classList.contains("light-theme") || 
                                     document.documentElement.classList.contains("light-theme");
            const newTheme = isCurrentlyLight ? "dark" : "light";
            localStorage.setItem("focus_theme", newTheme);
            updateThemeUI(newTheme);
        });
    });
});

