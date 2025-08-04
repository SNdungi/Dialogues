document.addEventListener('DOMContentLoaded', () => {

    // =================================================================
    // 1. ALL ELEMENT SELECTORS
    // =================================================================
    
    // Navigation Panels & Lists
    const mainNav = document.getElementById('main-nav');
    const subNav = document.getElementById('sub-nav');
    const subNavList = document.getElementById('sub-nav-list');
    const subNavTitle = document.getElementById('sub-nav-title');
    const discourseNav = document.getElementById('discourse-nav');
    const discourseNavList = document.getElementById('discourse-nav-list');
    const discourseNavTitle = document.getElementById('discourse-nav-title');

    // Main Content Display Elements
    const discourseTitle = document.getElementById('discourse-title');
    const discourseBody = document.getElementById('discourse-body');
    const discourseDate = document.getElementById('discourse-date');
    const discourseRef = document.getElementById('discourse-ref');
    const resourceList = document.getElementById('resource-list');
    const contributePrompt = document.getElementById('contribute-prompt');
    
    // Admin & Modal Elements
    const dropdownTrigger = document.getElementById('logo-dropdown-trigger');
    const dropdownMenu = document.getElementById('logo-dropdown-menu');
    // ... (other modal/form selectors if needed) ...

    // =================================================================
    // 2. HELPER FUNCTIONS
    // =================================================================

    /**
     * Manages the 'active' class for clicked links within a container.
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
     * Updates the main content area with data from a discourse object.
     */
    function updateMainContent(content) {
        if (!content) {
            // Default state if no content is found or provided
            if(discourseTitle) discourseTitle.textContent = 'Welcome to Dialogues of Light';
            if(discourseBody) discourseBody.innerHTML = '<p>Please select a topic from the navigation to begin a discourse.</p>';
            if(discourseDate) discourseDate.textContent = '';
            if(discourseRef) discourseRef.textContent = '';
            if(resourceList) resourceList.innerHTML = '';
            if(contributePrompt) contributePrompt.textContent = 'Join the conversation.';
            return;
        }

        // Update with content data, providing fallbacks
        if(discourseTitle) discourseTitle.textContent = content.title || 'Title Not Available';
        if(discourseBody) discourseBody.innerHTML = content.body || '<p>Content not available.</p>';
        if(discourseDate) discourseDate.textContent = content.date_posted || 'N/A';
        if(discourseRef) discourseRef.textContent = `Reference: ${content.reference || 'N/A'}`;
        if(contributePrompt) contributePrompt.textContent = `Share your thoughts on '${content.title || 'this topic'}'.`;

        // Rebuild the resources list
        if(resourceList) {
            resourceList.innerHTML = '';
            if (content.resources && content.resources.length > 0) {
                content.resources.forEach(res => {
                    const li = document.createElement('li');
                    const typeChar = res.type ? (res.type.value || res.type)[0].toUpperCase() : '?';
                    li.innerHTML = `<span class="resource-type ${res.type}">${typeChar}</span><strong>${res.name}:</strong> ${res.link}`;
                    resourceList.appendChild(li);
                });
            }
        }
    }


    // =================================================================
    // 3. NAVIGATION EVENT LISTENERS
    // =================================================================

    // --- LEVEL 1: Main Categories ---
    if (mainNav) {
        mainNav.addEventListener('click', (e) => {
            const link = e.target.closest('.main-topic-link');
            if (!link) return;
            e.preventDefault();
            
            // Hide the third panel whenever a new main category is chosen
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

    // --- LEVEL 2: Subcategories ---
    if (subNav) {
        subNav.addEventListener('click', (e) => {
            const link = e.target.closest('a');
            if (!link) return;
            e.preventDefault();
            
            const subCategoryId = parseInt(link.dataset.subcategoryId, 10);
            
            // Find all discourses that belong to this subcategory
            const discoursesForSubcat = CONTENT_DATA.filter(c => c.subcategory_id === subCategoryId);

            if (discoursesForSubcat.length > 0) {
                updateActiveLink(subNavList, link);
                
                if (discourseNavTitle) discourseNavTitle.textContent = link.textContent;
                if (discourseNavList) {
                    discourseNavList.innerHTML = '';
                    // Sort by date, newest first, just in case
                    discoursesForSubcat.sort((a, b) => new Date(b.date_posted) - new Date(a.date_posted));
                    discoursesForSubcat.forEach(disc => {
                        const li = document.createElement('li');
                        // Use the discourse's main ID to fetch its full content
                        li.innerHTML = `<a href="#" data-discourse-id="${disc.id}">${disc.title}</a>`;
                        discourseNavList.appendChild(li);
                    });
                }
                if (discourseNav) discourseNav.classList.add('visible');
            } else {
                // If no discourses, hide the panel and show a message
                if (discourseNav) discourseNav.classList.remove('visible');
                updateMainContent({
                    title: `No Discourses in ${link.textContent}`,
                    body: '<p>Content for this topic is still being written. Please check back soon!</p>'
                });
            }
        });
    }

    // --- LEVEL 3: Discourse Titles ---
    if (discourseNav) {
        discourseNav.addEventListener('click', (e) => {
            const link = e.target.closest('a');
            if (!link) return;
            e.preventDefault();

            const discourseId = link.dataset.discourseId; // The ID is a string from the 'id' field of the discourse
            const content = CONTENT_DATA.find(c => c.id === discourseId);
            
            if (content) {
                updateActiveLink(discourseNavList, link);
                updateMainContent(content);
            }
        });
    }

    // --- Panel Closing Logic ---
    document.body.addEventListener('click', (e) => {
        const closeBtn = e.target.closest('.close-btn');
        if (!closeBtn) return;
        
        const panelId = closeBtn.dataset.closePanel;
        const panelToClose = document.getElementById(panelId);
        if (panelToClose) {
            panelToClose.classList.remove('visible');
            // If we close the sub-nav, also close the discourse-nav
            if (panelId === 'sub-nav') {
                if (discourseNav) discourseNav.classList.remove('visible');
            }
        }
    });

    // --- Admin Dropdown Logic ---
    if (dropdownTrigger) {
        // ... (This logic can be copied from the previous response, it doesn't need to change) ...
    }
    // ... (Modal logic also remains the same) ...

});