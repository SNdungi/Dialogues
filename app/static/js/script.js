// static/js/script.js

document.addEventListener('DOMContentLoaded', () => {

    // =================================================================
    // 1. ALL ELEMENT SELECTORS - Defined once at the top
    // =================================================================
    
    // For Main/Sub Navigation and Content Update
    const mainNav = document.getElementById('main-nav');
    const subNav = document.getElementById('sub-nav');
    const subNavTitle = document.getElementById('sub-nav-title');
    const subNavList = document.getElementById('sub-nav-list');
    const closeSubNavBtn = document.getElementById('close-sub-nav');
    const discourseTitle = document.getElementById('discourse-title');
    const discourseBody = document.getElementById('discourse-body');
    const resourceList = document.getElementById('resource-list');

    // For Admin Dropdown
    const dropdownTrigger = document.getElementById('logo-dropdown-trigger');
    const dropdownMenu = document.getElementById('logo-dropdown-menu');
    
    // For Modals (generic selectors)
    const openModalButtons = document.querySelectorAll('[data-modal-target]');
    const closeModalButtons = document.querySelectorAll('[data-modal-close]');
    const overlays = document.querySelectorAll('.modal-overlay');

    // For Forms
    const imageForm = document.getElementById('image-form');
    const imageFileInput = document.getElementById('image-file');
    const imagePreview = document.getElementById('image-preview');
    const imageStatus = document.getElementById('image-status');
    const discourseForm = document.getElementById('discourse-form');
    const discourseStatus = document.getElementById('discourse-status');
    const joinForm = document.getElementById('join-form');
    
    // =================================================================
    // 2. ALL FUNCTIONS - Grouped together for clarity
    // =================================================================

    /**
     * Hides the sub-navigation panel.
     */
    function hideSubNav() {
        if (subNav) subNav.classList.remove('visible');
        // Deactivate main topic link when its panel is closed
        const activeMainLink = mainNav ? mainNav.querySelector('.main-topic-link.active') : null;
        if (activeMainLink) activeMainLink.classList.remove('active');
    }

    /**
     * Manages the 'active' class for clicked links within a container.
     * @param {HTMLElement} container - The navigation container (e.g., mainNav or subNavList).
     * @param {HTMLElement} activeLink - The link element that was clicked.
     */
    function updateActiveLink(container, activeLink) {
        if (!container || !activeLink) return;
        const currentActive = container.querySelector('.active');
        if (currentActive) {
            currentActive.classList.remove('active');
        }
        activeLink.classList.add('active');
    }

    /**
     * Opens a modal and its corresponding overlay.
     * @param {HTMLElement} modal - The modal element to open.
     */
    const openModal = (modal) => {
        if (modal == null) return;
        const overlay = document.getElementById(modal.id + '-overlay');
        modal.classList.add('active', 'visible'); // Use both for compatibility if CSS depends on them
        if (overlay) overlay.classList.add('active', 'visible');
        if (dropdownMenu) dropdownMenu.classList.remove('visible'); // Always hide dropdown when opening a modal
    };

    /**
     * Closes any active modal and its overlay.
     */
    const closeModal = () => {
        document.querySelectorAll('.modal.active, .modal.visible').forEach(modal => {
            modal.classList.remove('active', 'visible');
        });
        document.querySelectorAll('.modal-overlay.active, .modal-overlay.visible').forEach(overlay => {
            overlay.classList.remove('active', 'visible');
        });
    };
    
    // =================================================================
    // 3. ALL EVENT LISTENERS - Attached once after functions are defined
    // =================================================================

    // --- Navigation Logic ---
    if (mainNav) {
        mainNav.addEventListener('click', (e) => {
            const link = e.target.closest('.main-topic-link');
            if (!link) return;

            e.preventDefault();
            // This relies on global TOPICS_DATA injected in layout.html
            const topicId = link.dataset.topicId;
            const topicData = TOPICS_DATA.find(t => t.id === topicId);
            
            if (topicData) {
                updateActiveLink(mainNav, link);
                // Populate Sub-Nav
                if (subNavTitle) subNavTitle.textContent = topicData.name;
                if (subNavList) {
                    subNavList.innerHTML = ''; // Clear previous items
                    topicData.subtopics.forEach(sub => {
                        const li = document.createElement('li');
                        li.innerHTML = `<a href="#" data-content-id="${sub.id}">${sub.name}</a>`;
                        subNavList.appendChild(li);
                    });
                }
                if (subNav) subNav.classList.add('visible');
            }
        });
    }

    if (subNav) {
        subNav.addEventListener('click', (e) => {
            const link = e.target.closest('a');
            if (!link) return;

            e.preventDefault();
            // This relies on global CONTENT_DATA injected in layout.html
            const contentId = link.dataset.contentId;
            const content = CONTENT_DATA.find(c => c.id === contentId); // Assumes CONTENT_DATA is an array

            if (content) {
                // Update Main Content
                if (discourseTitle) discourseTitle.textContent = content.title;
                if (discourseBody) discourseBody.innerHTML = content.body;
                if (resourceList) {
                    resourceList.innerHTML = ''; // Clear old resources
                    if (content.resources && content.resources.length > 0) {
                        content.resources.forEach(res => {
                            const li = document.createElement('li');
                            li.innerHTML = `<span class="resource-type ${res.type}">${res.type[0]}</span><strong>${res.text}:</strong> ${res.ref}`;
                            resourceList.appendChild(li);
                        });
                    }
                }
                updateActiveLink(subNavList, link);
            } else {
                if (discourseTitle) discourseTitle.textContent = "Content Not Found";
                if (discourseBody) discourseBody.innerHTML = `<p>Content for '${link.textContent}' is not available.</p>`;
                if (resourceList) resourceList.innerHTML = "";
            }
        });
    }

    if (closeSubNavBtn) closeSubNavBtn.addEventListener('click', hideSubNav);

    // --- Admin Dropdown Logic ---
    if (dropdownTrigger) {
        dropdownTrigger.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent click from bubbling to the window
            dropdownMenu.classList.toggle('visible');
        });

        // Close dropdown if clicking anywhere else on the page
        window.addEventListener('click', (e) => {
            if (dropdownMenu && !dropdownTrigger.contains(e.target)) {
                dropdownMenu.classList.remove('visible');
            }
        });
    }

    // --- Generic Modal Trigger Logic ---
    openModalButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            const modal = document.getElementById(button.dataset.modalTarget);
            openModal(modal);
        });
    });

    closeModalButtons.forEach(button => button.addEventListener('click', closeModal));
    overlays.forEach(overlay => overlay.addEventListener('click', closeModal));

    // --- Form Submission Logic ---

    // 1. Join/Register Form
    if (joinForm) {
        joinForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const statusEl = document.getElementById('join-status');
            
            // --- ADD THIS VALIDATION BLOCK ---
            const password = document.getElementById('join-password').value;
            const passwordConf = document.getElementById('join-password-conf').value;

            if (password !== passwordConf) {
                statusEl.textContent = 'Error: Passwords do not match.';
                statusEl.className = 'status-message error';
                return; // Stop the form submission
            }
            // --- END OF VALIDATION BLOCK ---

            statusEl.textContent = 'Submitting...';
            statusEl.className = 'status-message';

            const formData = new FormData(joinForm);
            const data = Object.fromEntries(formData.entries());

            // ... (the rest of the fetch logic is unchanged and will work perfectly) ...
        });
    }
    
    // 2. Image Upload Form
    if (imageForm) {
        if(imageFileInput) {
            imageFileInput.addEventListener('change', () => {
                const file = imageFileInput.files[0];
                if (file && imagePreview) {
                    imagePreview.src = URL.createObjectURL(file);
                    imagePreview.style.display = 'block';
                }
            });
        }
        imageForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if(imageStatus) imageStatus.textContent = 'Uploading...';
            const formData = new FormData(imageForm);
            
            try {
                const response = await fetch('/upload-image', { method: 'POST', body: formData });
                const result = await response.json();
                if(imageStatus) imageStatus.textContent = result.message;
                if (result.status === 'success') {
                    imageForm.reset();
                    if(imagePreview) imagePreview.style.display = 'none';
                }
            } catch (error) {
                if(imageStatus) imageStatus.textContent = 'An error occurred during upload.';
            }
        });
    }

    // 3. Discourse Form
    if (discourseForm) {
        discourseForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if(discourseStatus) discourseStatus.textContent = 'Submitting...';
            const data = {
                title: document.getElementById('discourse-title-input').value, // Use unique ID for form input
                body: document.getElementById('discourse-body-input').value   // Use unique ID for form input
            };
            try {
                const response = await fetch('/add-discourse', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data),
                });
                const result = await response.json();
                if(discourseStatus) discourseStatus.textContent = result.message;
                if (result.status === 'success') {
                    discourseForm.reset();
                    setTimeout(() => location.reload(), 1500);
                }
            } catch (error) {
                if(discourseStatus) discourseStatus.textContent = 'An error occurred during submission.';
            }
        });
    }
});