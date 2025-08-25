// ==========================================================================
// Dialogues of Light - Authoritative Global JavaScript
// Handles all site-wide navigation, dropdowns, and modals.
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {

    // --- SECTION 1: GLOBAL STATE & ELEMENT CACHING ---
    // Cache elements that are part of the base layout for performance.
    const mainNav = document.getElementById('main-nav');
    const subNav = document.getElementById('sub-nav');
    const subNavList = document.getElementById('sub-nav-list');
    const subNavTitle = document.getElementById('sub-nav-title');
    const discourseNav = document.getElementById('discourse-nav');
    const discourseNavList = document.getElementById('discourse-nav-list');
    const discourseNavTitle = document.getElementById('discourse-nav-title');
    const dropdownTrigger = document.getElementById('logo-dropdown-trigger');
    const dropdownMenu = document.getElementById('logo-dropdown-menu');

    // --- SECTION 2: MODAL MANAGEMENT ---

    /**
     * Opens a modal and its corresponding overlay.
     * @param {HTMLElement} modal The modal element to open.
     */
    function openModal(modal) {
        if (!modal) return;
        const overlay = document.getElementById(modal.id + '-overlay');
        modal.classList.add('visible');
        if (overlay) overlay.classList.add('visible');
        if (dropdownMenu) dropdownMenu.classList.remove('visible'); // Close admin dropdown
    }

    /**
     * Closes all currently visible modals and overlays.
     */
    function closeModal() {
        document.querySelectorAll('.modal.visible').forEach(m => m.classList.remove('visible'));
        document.querySelectorAll('.modal-overlay.visible').forEach(o => o.classList.remove('visible'));
    }


    // --- SECTION 3: NAVIGATION PANEL LOGIC ---

    /**
     * Updates the active link styling within a navigation container.
     * @param {HTMLElement} container The navigation panel (e.g., mainNav, subNavList).
     * @param {HTMLElement} activeLink The link element that was clicked.
     */
    function updateActiveLink(container, activeLink) {
        if (!container || !activeLink) return;
        const currentActive = container.querySelector('.active');
        if (currentActive) currentActive.classList.remove('active');
        activeLink.classList.add('active');
    }

    /** Closes all slide-out navigation panels. */
    function closeAllNavPanels() {
        if (subNav) subNav.classList.remove('visible');
        if (discourseNav) discourseNav.classList.remove('visible');
    }

    /**
     * Handles clicks on the main category navigation.
     * @param {Event} e The click event.
     */
    function handleCategoryClick(e) {
        const link = e.target.closest('.main-topic-link');
        if (!link) return;
        e.preventDefault();

        closeAllNavPanels(); // Close everything first for a clean state
        const categoryId = parseInt(link.dataset.topicId, 10);
        const categoryData = SIDEBAR_DATA.find(cat => cat.id === categoryId);

        if (categoryData && categoryData.subcategories.length > 0) {
            updateActiveLink(mainNav, link);
            if (subNavTitle) subNavTitle.textContent = categoryData.name;
            if (subNavList) {
                subNavList.innerHTML = ''; // Clear previous items
                categoryData.subcategories.forEach(sub => {
                    const li = document.createElement('li');
                    li.innerHTML = `<a href="#" data-subcategory-id="${sub.id}">${sub.name}</a>`;
                    subNavList.appendChild(li);
                });
            }
            if (subNav) subNav.classList.add('visible');
        }
    }

    /**
     * Handles clicks on the subcategory navigation panel.
     * @param {Event} e The click event.
     */
    function handleSubcategoryClick(e) {
        const link = e.target.closest('a');
        if (!link) return;
        e.preventDefault();

        if (discourseNav) discourseNav.classList.remove('visible');
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
            // Handle case where subcategory has no discourses
            const discourseContentSection = document.getElementById('discourse-section');
            if (discourseContentSection) {
                updateDiscourseContent({
                    title: `No Discourses in ${link.textContent}`,
                    body: '<p>Content is being prepared for this topic. Please check back later.</p>',
                    date_posted: '', reference: '', resources: []
                });
            }
        }
    }
    
    /**
     * Handles clicks on discourse links in the third navigation panel.
     * This is the "smart" router function.
     * - If on the dialogues page, it updates the content via AJAX.
     * - If on any other page, it redirects to the dialogues page with the correct discourse ID.
     * @param {Event} e The click event.
     */
    async function handleDiscourseLinkClick(e) {
        const link = e.target.closest('a');
        if (!link) return;
        e.preventDefault();
        
        const discourseId = link.dataset.discourseId;
        if (!discourseId) return;

        // Check if we are on the dialogues page by looking for a key content element.
        const discourseContentSection = document.getElementById('discourse-section');

        if (discourseContentSection) {
            // --- PATH 1: We are on the dialogues page. Use AJAX for a smooth update. ---
            console.log(`On dialogues page. Fetching content for discourse ID: ${discourseId}`);
            updateActiveLink(discourseNavList, link);
            
            // Set a loading state immediately for better UX
            discourseContentSection.style.opacity = '0.5';

            try {
                const response = await fetch(`/discourse/api/get/${discourseId}`);
                if (!response.ok) throw new Error(`HTTP error ${response.status}`);
                const result = await response.json();

                if (result.status === 'success' && result.discourse) {
                    updateDiscourseContent(result.discourse);
                } else {
                    updateDiscourseContent({ title: 'Error', body: `<p>${result.message || 'Could not load content.'}</p>` });
                }
            } catch (error) {
                console.error("Fetch error:", error);
                updateDiscourseContent({ title: 'Network Error', body: '<p>Could not connect to the server to load content.</p>' });
            } finally {
                discourseContentSection.style.opacity = '1';
                closeAllNavPanels();
            }

        } else {
            // --- PATH 2: We are NOT on the dialogues page (e.g., editor). Redirect. ---
            console.log(`Not on dialogues page. Redirecting to show discourse ID: ${discourseId}`);
            window.location.href = `/discourse/dialogues?discourse_id=${discourseId}`;
        }
    }

    /**
     * A helper function to update all DOM elements on the dialogues page with new content.
     * @param {object} discourse The discourse object from the API.
     */
    function updateDiscourseContent(discourse) {
        // Cache elements specific to the dialogues page
        const titleEl = document.getElementById('discourse-title');
        const bodyEl = document.getElementById('discourse-body');
        const dateEl = document.getElementById('discourse-date');
        const refEl = document.getElementById('discourse-ref');
        const promptEl = document.getElementById('contribute-prompt');
        const imageContainer = document.getElementById('featured-image-container');
        const resourceList = document.getElementById('resource-list');

        // Update simple text elements if they exist
        if (titleEl) titleEl.textContent = discourse.title || 'N/A';
        if (dateEl) dateEl.textContent = discourse.date_posted || '';
        if (refEl) refEl.textContent = discourse.reference ? `Reference: ${discourse.reference}` : '';
        if (promptEl) promptEl.textContent = `Share your thoughts on '${discourse.title || 'this topic'}'.`;

        // Update HTML content
        if (bodyEl) bodyEl.innerHTML = discourse.body || '<p>Content not available.</p>';

        // Update featured image
        if (imageContainer) {
            imageContainer.innerHTML = ''; // Clear previous image
            if (discourse.featured_image_url) {
                const img = document.createElement('img');
                img.src = discourse.featured_image_url;
                img.alt = discourse.title;
                img.className = 'featured-image';
                imageContainer.appendChild(img);
            }
        }

        // Update resources list
        if (resourceList) {
            resourceList.innerHTML = ''; // Clear previous resources
            if (discourse.resources && discourse.resources.length > 0) {
                discourse.resources.forEach(resource => {
                    const li = document.createElement('li');
                    const typeInitial = resource.type ? resource.type[0] : '?';
                    const typeClass = resource.type ? resource.type.toLowerCase().replace(/\s+/g, '-') : 'unknown';
                    const iconClass = (resource.type === 'Scripture') ? 'fa-book-bible' : 'fa-link';

                    li.innerHTML = `
                        <span class="resource-type ${typeClass}">${typeInitial}</span>
                        <strong>${resource.name}:</strong> 
                        <a href="${resource.link}" target="_blank" rel="noopener noreferrer">
                            <i class="fas ${iconClass}" aria-hidden="true"></i>
                        </a>`;
                    resourceList.appendChild(li);
                });
            } else {
                resourceList.innerHTML = '<li>No resources are listed for this discourse.</li>';
            }
        }
    }


    // --- SECTION 4: GLOBAL EVENT LISTENERS & INITIALIZATION ---

    // Direct listeners for navigation panels
    if (mainNav) mainNav.addEventListener('click', handleCategoryClick);
    if (subNav) subNav.addEventListener('click', handleSubcategoryClick);
    if (discourseNav) discourseNav.addEventListener('click', handleDiscourseLinkClick);

    // Listener for the admin dropdown menu
    if (dropdownTrigger) {
        dropdownTrigger.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent body click from closing it immediately
            if (dropdownMenu) dropdownMenu.classList.toggle('visible');
        });
    }

    // A single, delegated event listener for the whole body
    document.body.addEventListener('click', (e) => {
        // --- Handle modal opening ---
        const modalTargetButton = e.target.closest('[data-modal-target]');
        if (modalTargetButton) {
            e.preventDefault();
            const modalId = modalTargetButton.dataset.modalTarget;
            const modal = document.getElementById(modalId);
            if (modal) {
                openModal(modal);
            } else {
                console.error(`Modal with ID #${modalId} not found.`);
            }
            return;
        }

        // --- Handle modal & dropdown closing ---
        const modalCloseButton = e.target.closest('[data-modal-close]');
        const isOverlay = e.target.classList.contains('modal-overlay');
        if (modalCloseButton || isOverlay) {
            closeModal();
            return;
        }
        // Close admin dropdown if clicking anywhere else
        if (dropdownMenu && !e.target.closest('#logo-dropdown-trigger') && !e.target.closest('#logo-dropdown-menu')) {
            dropdownMenu.classList.remove('visible');
        }

        // --- Handle navigation panel closing ---
        const closeBtn = e.target.closest('.close-btn');
        if (closeBtn) {
            const panelToClose = closeBtn.closest('.sub-nav, .discourse-nav');
            if (panelToClose) {
                panelToClose.classList.remove('visible');
                // If closing sub-nav, also close discourse-nav
                if (panelToClose.id === 'sub-nav' && discourseNav) {
                    discourseNav.classList.remove('visible');
                }
            }
        }
    });


    // --- SECTION 5: PAGE-SPECIFIC FORM LOGIC ---
    // These listeners will only attach if the relevant form is on the current page.

    const imageForm = document.getElementById('image-form');
    if (imageForm) {
        const imageFile = document.getElementById('image-file');
        const imagePreview = document.getElementById('image-preview');
        const statusMessage = document.getElementById('image-status');

        imageFile.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    imagePreview.src = e.target.result;
                    imagePreview.style.display = 'block';
                };
                reader.readAsDataURL(this.files[0]);
            }
        });

        imageForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            statusMessage.textContent = 'Uploading...';
            statusMessage.className = 'status-message saving';
            
            const formData = new FormData(imageForm);
            
            try {
                const response = await fetch('/upload-image', {
                    method: 'POST',
                    body: formData,
                });
                const result = await response.json();
                
                if (result.status === 'success') {
                    statusMessage.textContent = result.message;
                    statusMessage.className = 'status-message success';
                    setTimeout(() => {
                        imageForm.reset();
                        imagePreview.style.display = 'none';
                        closeModal();
                    }, 2000);
                } else {
                    statusMessage.textContent = `Error: ${result.message}`;
                    statusMessage.className = 'status-message error';
                }
            } catch (error) {
                console.error('Image upload error:', error);
                statusMessage.textContent = 'A network error occurred.';
                statusMessage.className = 'status-message error';
            }
        });
    }

async function populateDailyDevotions() {
    console.log("Attempting to populate daily devotions...");

    // Sidebar elements
    const readingTitleEl = document.getElementById('reading-title');
    if (!readingTitleEl) {
        console.log("Sidebar devotional elements not found on this page. Skipping fetch.");
        return;
    }

    try {
        const response = await fetch('/liturgy/daily-devotions');
        if (!response.ok) {
            console.error('Failed to fetch daily devotions. Status:', response.status);
            return;
        }

        const data = await response.json();
        console.log("Successfully fetched daily devotions data:", data);

        // --- 1. Daily Prayer ---
        const readingBodyEl = document.getElementById('reading-body');
        if (Array.isArray(data.prayers) && data.prayers.length > 0) {
            const firstPrayer = data.prayers[0] || {};
            const title = firstPrayer.title || 'Daily Prayer';
            const text = typeof firstPrayer.text === "string" ? firstPrayer.text : '';

            if (readingTitleEl) readingTitleEl.textContent = title;
            if (readingBodyEl) {
                readingBodyEl.innerHTML = text
                    ? text.replace(/\n/g, '<br>')
                    : 'Prayer content not available.';
            }
        } else {
            if (readingTitleEl) readingTitleEl.textContent = 'Daily Prayer';
            if (readingBodyEl) readingBodyEl.textContent = 'Prayer content not available.';
        }

        // --- 2. Saint of the Day ---
        const devotionTitleEl = document.getElementById('devotion-title');
        const devotionBodyEl = document.getElementById('devotion-body');
        const saint = data.saint_of_the_day || {};
        if (saint.title || saint.name) {
            if (devotionTitleEl) devotionTitleEl.textContent = saint.title || saint.name;
            if (devotionBodyEl) devotionBodyEl.textContent = saint.description || saint.bio || 'Saint details not available.';
        }

        // --- 3. Rosary Mysteries ---
        const prayerTitleEl = document.getElementById('prayer-title');
        const prayerBodyEl = document.getElementById('prayer-body');
        const rosary = data.rosary || {};
        if (rosary.title) {
            if (prayerTitleEl) prayerTitleEl.textContent = rosary.title;
            const mysteries = Array.isArray(rosary.mysteries) ? rosary.mysteries.join(', ') : 'Mysteries not available.';
            const targetPrayerBody = prayerBodyEl || document.querySelector('#daily-prayer em');
            if (targetPrayerBody) targetPrayerBody.textContent = mysteries;
        }

    } catch (error) {
        console.error('Network error while fetching daily devotions:', error);
    }
}


// Keep this call inside the main DOMContentLoaded listener
populateDailyDevotions();

}); // This is the closing brace for the main DOMContentLoaded listener at the top of the file                                                   M