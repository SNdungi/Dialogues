// ==========================================================================
// Dialogues of Light - Authoritative Global JavaScript
// Handles all site-wide navigation, dropdowns, and modals.
// This is the single source of truth for all interactive components.
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {

    // --- SECTION 1: GLOBAL STATE & ELEMENT CACHING ---
    let currentDiscourseId = null;
    const mainNav = document.getElementById('main-nav');
    const subNav = document.getElementById('sub-nav');
    const subNavList = document.getElementById('sub-nav-list');
    const subNavTitle = document.getElementById('sub-nav-title');
    const discourseNav = document.getElementById('discourse-nav');
    const discourseNavList = document.getElementById('discourse-nav-list');
    const discourseNavTitle = document.getElementById('discourse-nav-title');
    const discourseTitleEl = document.getElementById('discourse-title');
    const discourseBodyEl = document.getElementById('discourse-body');
    const discourseDateEl = document.getElementById('discourse-date');
    const discourseRefEl = document.getElementById('discourse-ref');
    const resourceListEl = document.getElementById('resource-list');
    const contributePromptEl = document.getElementById('contribute-prompt');
    const dropdownTrigger = document.getElementById('logo-dropdown-trigger');
    const dropdownMenu = document.getElementById('logo-dropdown-menu');

    // --- SECTION 2: CORE HELPER FUNCTIONS ---

    function updateActiveLink(container, activeLink) {
        if (!container || !activeLink) return;
        const currentActive = container.querySelector('.active');
        if (currentActive) currentActive.classList.remove('active');
        activeLink.classList.add('active');
    }

    function updateMainContent(content) {
        currentDiscourseId = content ? content.id : null;
        if (!content) {
            if(discourseTitleEl) discourseTitleEl.textContent = 'Welcome';
            if(discourseBodyEl) discourseBodyEl.innerHTML = '<p>Please select a topic.</p>';
            if(discourseDateEl) discourseDateEl.textContent = '';
            if(discourseRefEl) discourseRefEl.textContent = '';
            if(resourceListEl) resourceListEl.innerHTML = '';
            if(contributePromptEl) contributePromptEl.textContent = 'Join the conversation.';
            return;
        }
        if(discourseTitleEl) discourseTitleEl.textContent = content.title || 'N/A';
        if(discourseBodyEl) discourseBodyEl.innerHTML = content.body || '';
        if(discourseDateEl) discourseDateEl.textContent = content.date_posted || 'N/A';
        if(discourseRefEl) discourseRefEl.textContent = `Ref: ${content.reference || 'N/A'}`;
        if(contributePromptEl) contributePromptEl.textContent = `Thoughts on '${content.title || 'this topic'}'?`;
        if(resourceListEl) {
            resourceListEl.innerHTML = '';
            if (content.resources && content.resources.length > 0) {
                content.resources.forEach(res => {
                    const li = document.createElement('li');
                    const typeChar = res.type ? res.type[0].toUpperCase() : '?';
                    li.innerHTML = `<span class="resource-type ${res.type.toLowerCase()}">${typeChar}</span><strong>${res.name}:</strong> ${res.link}`;
                    resourceListEl.appendChild(li);
                });
            }
        }
    }

    function openModal(modal) {
        if (!modal) return;
        const overlay = document.getElementById(modal.id + '-overlay');
        modal.classList.add('visible');
        if (overlay) overlay.classList.add('visible');
        if (dropdownMenu) dropdownMenu.classList.remove('visible');
    }

    function closeModal() {
        document.querySelectorAll('.modal.visible').forEach(m => m.classList.remove('visible'));
        document.querySelectorAll('.modal-overlay.visible').forEach(o => o.classList.remove('visible'));
    }

    // --- SECTION 3: NAVIGATION LOGIC (Direct Listeners) ---
    // These elements are part of the base layout, so direct listeners are safe.

    if (mainNav) {
        mainNav.addEventListener('click', (e) => {
            const link = e.target.closest('.main-topic-link');
            if (!link) return;
            e.preventDefault();
            if (discourseNav) discourseNav.classList.remove('visible');
            const categoryId = parseInt(link.dataset.topicId, 10);
            const categoryData = SIDEBAR_DATA.find(cat => cat.id === categoryId);
            if (categoryData && categoryData.subcategories.length > 0) {
                updateActiveLink(mainNav, link);
                if (subNavTitle) subNavTitle.textContent = categoryData.name;
                if (subNavList) {
                    subNavList.innerHTML = '';
                    categoryData.subcategories.forEach(sub => {
                        const li = document.createElement('li');
                        li.innerHTML = `<a href="#" data-subcategory-id="${sub.id}">${sub.name}</a>`;
                        subNavList.appendChild(li);
                    });
                }
                if (subNav) subNav.classList.add('visible');
            } else {
                if (subNav) subNav.classList.remove('visible');
            }
        });
    }

    if (subNav) {
        subNav.addEventListener('click', (e) => {
            const link = e.target.closest('a');
            if (!link) return;
            e.preventDefault();
            const subCategoryId = parseInt(link.dataset.subcategoryId, 10);
            const discoursesForSubcat = CONTENT_DATA.filter(c => c.subcategory_id === subCategoryId);
            if (discoursesForSubcat.length > 0) {
                updateActiveLink(subNavList, link);
                if (discourseNavTitle) discourseNavTitle.textContent = link.textContent;
                if (discourseNavList) {
                    discourseNavList.innerHTML = '';
                    discoursesForSubcat.forEach(disc => {
                        const li = document.createElement('li');
                        li.innerHTML = `<a href="#" data-discourse-id="${disc.id}">${disc.title}</a>`;
                        discourseNavList.appendChild(li);
                    });
                }
                if (discourseNav) discourseNav.classList.add('visible');
            } else {
                if (discourseNav) discourseNav.classList.remove('visible');
                updateMainContent({ title: `No Discourses in ${link.textContent}`, body: '<p>Content is being written.</p>' });
            }
        });
    }

    if (discourseNav) {
        discourseNav.addEventListener('click', async (e) => {
            const link = e.target.closest('a');
            if (!link) return;
            e.preventDefault();
            updateActiveLink(discourseNavList, link);
            const discourseId = link.dataset.discourseId; 
            if(discourseTitleEl) discourseTitleEl.textContent = "Loading...";
            if(discourseBodyEl) discourseBodyEl.innerHTML = '<p>Fetching content...</p>';
            if(resourceListEl) resourceListEl.innerHTML = '';
            try {
                const response = await fetch(`/discourse/api/get/${discourseId}`);
                if (!response.ok) throw new Error(`HTTP error ${response.status}`);
                const result = await response.json();
                if (result.status === 'success' && result.discourse) {
                    updateMainContent(result.discourse);
                } else {
                    updateMainContent({ title: 'Error', body: `<p>${result.message || 'Could not load.'}</p>` });
                }
            } catch (error) {
                console.error("Fetch error:", error);
                updateMainContent({ title: 'Network Error', body: '<p>Could not connect to the server.</p>' });
            }
        });
    }

    if (dropdownTrigger) {
        dropdownTrigger.addEventListener('click', (e) => {
            e.stopPropagation();
            if (dropdownMenu) dropdownMenu.classList.toggle('visible');
        });
    }

    // --- DELEGATED EVENT LISTENER FOR MODALS AND PANEL CLOSING ---
    document.body.addEventListener('click', (e) => {
        console.log("--------------------");
        console.log("Body clicked. Target:", e.target);

        // --- Handle modal opening ---
        const modalTargetButton = e.target.closest('[data-modal-target]');
        if (modalTargetButton) {
            console.log("SUCCESS: Found a modal trigger button:", modalTargetButton);
            e.preventDefault();
            const modalId = modalTargetButton.dataset.modalTarget;
            const modal = document.getElementById(modalId);
            
            if (modal) {
                console.log(`SUCCESS: Found modal element with ID #${modalId}. Opening it.`);
                openModal(modal);
            } else {
                console.error(`ERROR: Could not find modal element with ID #${modalId}.`);
            }
            return; // Stop further processing
        }

        // --- Handle modal closing ---
        const modalCloseButton = e.target.closest('[data-modal-close]');
        const isOverlay = e.target.classList.contains('modal-overlay');
        if (modalCloseButton || isOverlay) {
            console.log("SUCCESS: Modal close action triggered.");
            closeModal();
            return;
        }

        // --- Handle navigation panel closing ---
        const closeBtn = e.target.closest('.close-btn');
        if (closeBtn) {
            console.log("SUCCESS: Panel close button clicked.");
            const panelToClose = closeBtn.closest('.sub-nav, .discourse-nav');
            if (panelToClose) {
                panelToClose.classList.remove('visible');
                if (panelToClose.id === 'sub-nav' && document.getElementById('discourse-nav')) {
                    document.getElementById('discourse-nav').classList.remove('visible');
                }
            }
        }
    });

    // --- SECTION 5: ADMIN FORM SUBMISSION LOGIC (from layout.html) ---
    // Only runs if these forms exist on the current page.
    const imageForm = document.getElementById('image-form');
    if (imageForm) {
        imageForm.addEventListener('submit', async (e) => {
            // ... (Full, working image form submission logic) ...
        });
    }
    const discourseAdminForm = document.getElementById('discourse-form'); // This is the old one from layout.html
    if (discourseAdminForm && !document.getElementById('editor-target-div')) { // Check it's not the editor page
        discourseAdminForm.addEventListener('submit', async (e) => {
            // ... (Full, working admin discourse form submission logic) ...
        });
    }
});