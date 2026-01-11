/*
 * Gallery and Lightbox Functionality
 */

// Initialize gallery when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initLightbox();
});

/**
 * Lightbox Functionality
 */
function initLightbox() {
    const lightbox = document.getElementById('lightbox');
    if (!lightbox) return;

    const lightboxOverlay = document.getElementById('lightbox-overlay');
    const lightboxClose = document.getElementById('lightbox-close');
    const lightboxImage = document.getElementById('lightbox-image');
    const lightboxCaption = document.getElementById('lightbox-caption');
    const lightboxPrev = document.getElementById('lightbox-prev');
    const lightboxNext = document.getElementById('lightbox-next');

    let currentImages = [];
    let currentIndex = 0;

    // Close lightbox
    function closeLightbox() {
        lightbox.classList.remove('active');
        document.body.style.overflow = '';
        currentImages = [];
        currentIndex = 0;
    }

    // Open lightbox with image
    window.openLightbox = function(imageSrc, caption) {
        lightboxImage.src = imageSrc;
        lightboxCaption.textContent = caption || '';
        lightbox.classList.add('active');
        document.body.style.overflow = 'hidden';

        // Collect all images in the same gallery
        const currentGallery = findParentGallery(event.target);
        if (currentGallery) {
            currentImages = Array.from(currentGallery.querySelectorAll('img')).map(img => ({
                src: img.src,
                caption: img.alt || ''
            }));
            currentIndex = currentImages.findIndex(img => img.src === imageSrc);
        }
    };

    // Find parent gallery element
    function findParentGallery(element) {
        while (element && element !== document.body) {
            if (element.classList.contains('project-gallery') ||
                element.classList.contains('gallery-grid')) {
                return element;
            }
            element = element.parentElement;
        }
        return null;
    }

    // Show previous image
    function showPrevImage() {
        if (currentImages.length === 0) return;

        currentIndex = (currentIndex - 1 + currentImages.length) % currentImages.length;
        lightboxImage.src = currentImages[currentIndex].src;
        lightboxCaption.textContent = currentImages[currentIndex].caption;
    }

    // Show next image
    function showNextImage() {
        if (currentImages.length === 0) return;

        currentIndex = (currentIndex + 1) % currentImages.length;
        lightboxImage.src = currentImages[currentIndex].src;
        lightboxCaption.textContent = currentImages[currentIndex].caption;
    }

    // Event listeners
    if (lightboxClose) {
        lightboxClose.addEventListener('click', closeLightbox);
    }

    if (lightboxOverlay) {
        lightboxOverlay.addEventListener('click', closeLightbox);
    }

    if (lightboxPrev) {
        lightboxPrev.addEventListener('click', function(e) {
            e.stopPropagation();
            showPrevImage();
        });
    }

    if (lightboxNext) {
        lightboxNext.addEventListener('click', function(e) {
            e.stopPropagation();
            showNextImage();
        });
    }

    // Keyboard navigation
    document.addEventListener('keydown', function(e) {
        if (!lightbox.classList.contains('active')) return;

        if (e.key === 'Escape') {
            closeLightbox();
        } else if (e.key === 'ArrowLeft') {
            showPrevImage();
        } else if (e.key === 'ArrowRight') {
            showNextImage();
        }
    });

    // Prevent image dragging
    if (lightboxImage) {
        lightboxImage.addEventListener('dragstart', function(e) {
            e.preventDefault();
        });
    }
}

/**
 * Load Gallery Images from JSON
 */
async function loadGalleryImages(jsonPath, containerId) {
    try {
        const response = await fetch(jsonPath);
        const data = await response.json();

        if (!data.images || data.images.length === 0) {
            return;
        }

        const container = document.getElementById(containerId);
        if (!container) return;

        const galleryHtml = data.images.map((imageSrc, index) => `
            <img
                src="${imageSrc}"
                alt="${data.title || 'Gallery image'} - ${index + 1}"
                loading="lazy"
                onclick="openLightbox('${imageSrc}', '${data.title || 'Gallery image'} - Image ${index + 1}')"
            >
        `).join('');

        container.innerHTML = `<div class="gallery-grid">${galleryHtml}</div>`;
    } catch (error) {
        console.error('Error loading gallery:', error);
    }
}

/**
 * Load Gallery Videos from JSON
 */
async function loadGalleryVideos(jsonPath, containerId) {
    try {
        const response = await fetch(jsonPath);
        const data = await response.json();

        if (!data.videos || data.videos.length === 0) {
            return;
        }

        const container = document.getElementById(containerId);
        if (!container) return;

        const videosHtml = data.videos.map(video => `
            <div class="video-container">
                <video controls ${video.thumbnail ? `poster="${video.thumbnail}"` : ''}>
                    <source src="${video.src}" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
                ${video.title ? `<p class="video-title">${video.title}</p>` : ''}
            </div>
        `).join('');

        container.innerHTML = videosHtml;
    } catch (error) {
        console.error('Error loading videos:', error);
    }
}

/**
 * Create Thumbnail Grid from Images
 */
function createThumbnailGrid(images, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const gridHtml = images.map((image, index) => `
        <div class="thumbnail" onclick="openLightbox('${image.src}', '${image.caption || ''}')">
            <img src="${image.thumbnail || image.src}" alt="${image.caption || `Image ${index + 1}`}" loading="lazy">
        </div>
    `).join('');

    container.innerHTML = `<div class="thumbnail-grid">${gridHtml}</div>`;
}

/**
 * Masonry Layout (if needed)
 * Creates a Pinterest-style grid layout
 */
function initMasonryLayout(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Simple masonry using CSS Grid (already implemented in CSS)
    // This function can be extended for more complex layouts

    const images = container.querySelectorAll('img');
    images.forEach(img => {
        img.addEventListener('load', function() {
            // Recalculate layout after image loads
            if (container.classList.contains('masonry')) {
                updateMasonryLayout(container);
            }
        });
    });
}

function updateMasonryLayout(container) {
    // Placeholder for masonry layout updates
    // Can be implemented with libraries like Masonry.js if needed
}

/**
 * Image Lazy Loading Enhancement
 */
function enhanceLazyLoading() {
    const images = document.querySelectorAll('img[loading="lazy"]');

    const imageObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                // Add a fade-in effect when image loads
                img.addEventListener('load', function() {
                    img.style.opacity = '0';
                    img.style.transition = 'opacity 0.3s ease-in-out';
                    setTimeout(() => img.style.opacity = '1', 10);
                });
                imageObserver.unobserve(img);
            }
        });
    });

    images.forEach(img => imageObserver.observe(img));
}

// Export functions for external use
window.galleryUtils = {
    loadGalleryImages,
    loadGalleryVideos,
    createThumbnailGrid,
    initMasonryLayout
};
