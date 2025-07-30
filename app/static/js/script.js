// static/js/script.js

document.addEventListener('DOMContentLoaded', () => {

    // --- ELEMENT SELECTORS ---
    const mainNav = document.getElementById('main-nav');
    const subNav = document.getElementById('sub-nav');
    const subNavTitle = document.getElementById('sub-nav-title');
    const subNavList = document.getElementById('sub-nav-list');
    const closeSubNavBtn = document.getElementById('close-sub-nav');

    const discourseTitle = document.getElementById('discourse-title');
    const discourseBody = document.getElementById('discourse-body');
    const resourceList = document.getElementById('resource-list');
    
    let currentMainTopic = null;

    // --- EVENT LISTENERS ---

    // 1. Listen for clicks on the Main Navigation
    mainNav.addEventListener('click', (e) => {
        const link = e.target.closest('.main-topic-link');
        if (!link) return;

        e.preventDefault();
        const topicId = link.dataset.topicId;
        const topicData = TOPICS_DATA.find(t => t.id === topicId);
        
        if (topicData) {
            updateActiveLink(mainNav, link);
            populateAndShowSubNav(topicData);
            currentMainTopic = topicId;
        }
    });

    // 2. Listen for clicks on the Sub Navigation
    subNav.addEventListener('click', (e) => {
        const link = e.target.closest('a');
        if (!link) return;

        e.preventDefault();
        const contentId = link.dataset.contentId;
        const content = CONTENT_DATA[contentId];

        if (content) {
            updateMainContent(content);
            updateActiveLink(subNavList, link);
            // Optional: close sub-nav after selection
            // hideSubNav();
        } else {
            // Handle case where content isn't found
            discourseTitle.textContent = "Content Coming Soon";
            discourseBody.innerHTML = `<p>The discourse for '${link.textContent}' is currently being prepared. Please check back later.</p>`;
            resourceList.innerHTML = "";
        }
    });

    // 3. Listen for click on the "Close" button for the sub-nav
    closeSubNavBtn.addEventListener('click', hideSubNav);


    // --- FUNCTIONS ---

    /**
     * Populates the sub-navigation panel with topics and makes it visible.
     * @param {object} topic - The main topic object from TOPICS_DATA.
     */
    function populateAndShowSubNav(topic) {
        subNavTitle.textContent = topic.name;
        subNavList.innerHTML = ''; // Clear previous items

        topic.subtopics.forEach(sub => {
            const li = document.createElement('li');
            li.innerHTML = `<a href="#" data-content-id="${sub.id}">${sub.name}</a>`;
            subNavList.appendChild(li);
        });

        subNav.classList.add('visible');
    }

    /**
     * Hides the sub-navigation panel.
     */
    function hideSubNav() {
        subNav.classList.remove('visible');
        // Deactivate main topic link when its panel is closed
        const activeMainLink = mainNav.querySelector('.main-topic-link.active');
        if(activeMainLink) activeMainLink.classList.remove('active');
    }
    
    /**
     * Updates the main content area with new data.
     * @param {object} content - The content object from CONTENT_DATA.
     */
    function updateMainContent(content) {
        discourseTitle.textContent = content.title;
        discourseBody.innerHTML = content.body;

        resourceList.innerHTML = ''; // Clear old resources
        if (content.resources && content.resources.length > 0) {
            content.resources.forEach(res => {
                const li = document.createElement('li');
                li.innerHTML = `
                    <span class="resource-type ${res.type}">${res.type}</span>
                    <strong>${res.text}:</strong> ${res.ref}
                `;
                resourceList.appendChild(li);
            });
        }
    }

    /**
     * Manages the 'active' class for clicked links within a container.
     * @param {HTMLElement} container - The navigation container (e.g., mainNav or subNavList).
     * @param {HTMLElement} activeLink - The link element that was clicked.
     */
    function updateActiveLink(container, activeLink) {
        const currentActive = container.querySelector('.active');
        if (currentActive) {
            currentActive.classList.remove('active');
        }
        activeLink.classList.add('active');
    }

    // === NEW LOGIC FOR ADMIN DROPDOWN AND MODALS ===   

    const dropdownTrigger = document.getElementById('logo-dropdown-trigger');
    const dropdownMenu = document.getElementById('logo-dropdown-menu');

    // 1. Dropdown Toggle Logic
    if (dropdownTrigger) {
        dropdownTrigger.addEventListener('click', (e) => {
            // Prevent clicks on links inside the dropdown from closing it immediately
            if (!e.target.closest('a')) {
                dropdownMenu.classList.toggle('visible');
            }
        });

        // Close dropdown if clicking outside
        window.addEventListener('click', (e) => {
            if (!dropdownTrigger.contains(e.target)) {
                dropdownMenu.classList.remove('visible');
            }
        });
    }

    // 2. Modal Control Logic
    const modalTriggers = document.querySelectorAll('[data-modal-target]');
    const closeButtons = document.querySelectorAll('.modal-close');
    const overlays = document.querySelectorAll('.modal-overlay');

    modalTriggers.forEach(trigger => {
        trigger.addEventListener('click', (e) => {
            e.preventDefault();
            const modalId = trigger.getAttribute('data-modal-target');
            const modal = document.getElementById(modalId);
            const overlay = document.getElementById(`${modalId}-overlay`);
            
            modal.classList.add('visible');
            overlay.classList.add('visible');
            dropdownMenu.classList.remove('visible'); // Hide dropdown after opening modal
        });
    });

    const closeModal = () => {
        document.querySelectorAll('.modal.visible').forEach(modal => modal.classList.remove('visible'));
        document.querySelectorAll('.modal-overlay.visible').forEach(overlay => overlay.classList.remove('visible'));
    };

    closeButtons.forEach(button => button.addEventListener('click', closeModal));
    overlays.forEach(overlay => overlay.addEventListener('click', closeModal));

    // 3. Image Upload Form Logic
    const imageForm = document.getElementById('image-form');
    const imageFileInput = document.getElementById('image-file');
    const imagePreview = document.getElementById('image-preview');
    const imageStatus = document.getElementById('image-status');

    if (imageForm) {
        imageFileInput.addEventListener('change', () => {
            const file = imageFileInput.files[0];
            if (file) {
                imagePreview.src = URL.createObjectURL(file);
                imagePreview.style.display = 'block';
            }
        });

        imageForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            imageStatus.textContent = 'Uploading...';
            const formData = new FormData(imageForm);
            
            try {
                const response = await fetch('/upload-image', {
                    method: 'POST',
                    body: formData,
                });
                const result = await response.json();
                imageStatus.textContent = result.message;
                if (result.status === 'success') {
                    imageForm.reset();
                    imagePreview.style.display = 'none';
                }
            } catch (error) {
                imageStatus.textContent = 'An error occurred during upload.';
            }
        });
    }

    // 4. Discourse Form Logic
    const discourseForm = document.getElementById('discourse-form');
    const discourseStatus = document.getElementById('discourse-status');

    if (discourseForm) {
        discourseForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            discourseStatus.textContent = 'Submitting...';

            const title = document.getElementById('discourse-title').value;
            const body = document.getElementById('discourse-body').value;

            try {
                const response = await fetch('/add-discourse', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title, body }),
                });
                const result = await response.json();
                discourseStatus.textContent = result.message;
                if (result.status === 'success') {
                    discourseForm.reset();
                    // Reload the page to see the new discourse slide
                    setTimeout(() => location.reload(), 1500);
                }
            } catch (error) {
                discourseStatus.textContent = 'An error occurred during submission.';
            }
        });
    }

});