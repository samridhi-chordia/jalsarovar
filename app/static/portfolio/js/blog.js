/*
 * Blog Functionality
 * Load and display blog posts dynamically
 */

document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('blog-grid')) {
        initBlog();
    }
});

/**
 * Initialize Blog
 */
async function initBlog() {
    try {
        const articles = await loadBlogArticles();

        if (articles && articles.length > 0) {
            displayBlogPosts(articles);
            initBlogFilters(articles);
            initBlogSearch(articles);
        }
    } catch (error) {
        console.error('Error loading blog:', error);
    }
}

/**
 * Load Blog Articles from JSON
 */
async function loadBlogArticles() {
    try {
        const response = await fetch('content/blog/articles.json');
        const data = await response.json();
        return data.articles || [];
    } catch (error) {
        console.log('No blog articles available yet');
        return [];
    }
}

/**
 * Display Blog Posts
 */
function displayBlogPosts(articles) {
    const grid = document.getElementById('blog-grid');
    if (!grid) return;

    // Remove placeholder
    const placeholder = grid.querySelector('.blog-placeholder');
    if (placeholder) placeholder.remove();

    // Sort by date (newest first)
    articles.sort((a, b) => new Date(b.date) - new Date(a.date));

    const html = articles.map(article => createBlogCard(article)).join('');
    grid.innerHTML = html;
}

/**
 * Create Blog Card HTML
 */
function createBlogCard(article) {
    return `
        <article class="blog-card" data-category="${article.category || 'general'}" data-tags="${(article.tags || []).join(' ')}">
            ${article.image ? `
                <div class="blog-image">
                    <img src="${article.image}" alt="${article.title}" loading="lazy">
                </div>
            ` : ''}
            <div class="blog-content">
                <div class="blog-meta">
                    <span class="blog-date">${formatBlogDate(article.date)}</span>
                    ${article.readTime ? `<span class="blog-read-time">${article.readTime} min read</span>` : ''}
                </div>
                <h3 class="blog-title">
                    <a href="content/blog/posts/${article.slug}.html">${article.title}</a>
                </h3>
                <p class="blog-excerpt">${article.excerpt}</p>
                ${article.tags && article.tags.length > 0 ? `
                    <div class="blog-tags">
                        ${article.tags.map(tag => `<span class="blog-tag">${tag}</span>`).join('')}
                    </div>
                ` : ''}
                <a href="content/blog/posts/${article.slug}.html" class="blog-read-more">Read More →</a>
            </div>
        </article>
    `;
}

/**
 * Format Blog Date
 */
function formatBlogDate(dateString) {
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return new Date(dateString).toLocaleDateString('en-US', options);
}

/**
 * Initialize Blog Filters
 */
function initBlogFilters(articles) {
    // Get unique categories
    const categories = [...new Set(articles.map(a => a.category || 'general'))];

    if (categories.length <= 1) return; // No need for filters if only one category

    // Create filter buttons
    const filterContainer = document.createElement('div');
    filterContainer.className = 'blog-filters';
    filterContainer.style.marginBottom = '2rem';
    filterContainer.style.textAlign = 'center';

    const buttons = `
        <button class="filter-btn active" data-category="all">All Posts</button>
        ${categories.map(cat => `
            <button class="filter-btn" data-category="${cat}">${capitalize(cat)}</button>
        `).join('')}
    `;

    filterContainer.innerHTML = buttons;

    const blogSection = document.querySelector('.blog-posts .container');
    const grid = document.getElementById('blog-grid');
    if (blogSection && grid) {
        blogSection.insertBefore(filterContainer, grid);
    }

    // Add click handlers
    filterContainer.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            // Update active state
            filterContainer.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');

            // Filter articles
            const category = this.dataset.category;
            filterBlogPosts(category);
        });
    });
}

/**
 * Filter Blog Posts
 */
function filterBlogPosts(category) {
    const cards = document.querySelectorAll('.blog-card');

    cards.forEach(card => {
        if (category === 'all' || card.dataset.category === category) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });

    // Show "no results" message if needed
    const visibleCards = Array.from(cards).filter(card => card.style.display !== 'none');
    const grid = document.getElementById('blog-grid');

    if (visibleCards.length === 0) {
        showNoResults(grid);
    } else {
        removeNoResults(grid);
    }
}

/**
 * Initialize Blog Search
 */
function initBlogSearch(articles) {
    // Create search input
    const searchContainer = document.createElement('div');
    searchContainer.className = 'blog-search';
    searchContainer.style.marginBottom = '2rem';
    searchContainer.style.maxWidth = '500px';
    searchContainer.style.margin = '0 auto 2rem';

    searchContainer.innerHTML = `
        <input
            type="text"
            id="blog-search-input"
            placeholder="Search blog posts..."
            style="width: 100%; padding: 0.75rem 1rem; border: 2px solid var(--border-color); border-radius: 0.5rem; font-size: 1rem;"
        >
    `;

    const blogSection = document.querySelector('.blog-posts .container');
    const grid = document.getElementById('blog-grid');

    if (blogSection && grid) {
        blogSection.insertBefore(searchContainer, grid);
    }

    // Add search functionality
    const searchInput = document.getElementById('blog-search-input');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(function(e) {
            searchBlogPosts(e.target.value);
        }, 300));
    }
}

/**
 * Search Blog Posts
 */
function searchBlogPosts(query) {
    const cards = document.querySelectorAll('.blog-card');
    const searchTerm = query.toLowerCase();

    cards.forEach(card => {
        const title = card.querySelector('.blog-title').textContent.toLowerCase();
        const excerpt = card.querySelector('.blog-excerpt').textContent.toLowerCase();
        const tags = card.dataset.tags.toLowerCase();

        if (title.includes(searchTerm) || excerpt.includes(searchTerm) || tags.includes(searchTerm)) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });

    // Show "no results" message if needed
    const visibleCards = Array.from(cards).filter(card => card.style.display !== 'none');
    const grid = document.getElementById('blog-grid');

    if (visibleCards.length === 0) {
        showNoResults(grid, `No posts found for "${query}"`);
    } else {
        removeNoResults(grid);
    }
}

/**
 * Show No Results Message
 */
function showNoResults(container, message = 'No posts found') {
    removeNoResults(container); // Remove existing message

    const noResults = document.createElement('div');
    noResults.className = 'no-results-message';
    noResults.style.textAlign = 'center';
    noResults.style.padding = '3rem';
    noResults.style.color = 'var(--text-light)';
    noResults.innerHTML = `
        <p style="font-size: 1.125rem; margin-bottom: 0.5rem;">📭</p>
        <p>${message}</p>
    `;

    container.appendChild(noResults);
}

/**
 * Remove No Results Message
 */
function removeNoResults(container) {
    const existing = container.querySelector('.no-results-message');
    if (existing) existing.remove();
}

/**
 * Calculate Reading Time
 */
function calculateReadingTime(text) {
    const wordsPerMinute = 200;
    const wordCount = text.trim().split(/\s+/).length;
    const readTime = Math.ceil(wordCount / wordsPerMinute);
    return readTime;
}

/**
 * Load Individual Blog Post
 * (For when viewing a single post)
 */
async function loadBlogPost(slug) {
    try {
        const response = await fetch(`content/blog/posts/${slug}.html`);
        const html = await response.text();

        const contentContainer = document.getElementById('blog-post-content');
        if (contentContainer) {
            contentContainer.innerHTML = html;
        }
    } catch (error) {
        console.error('Error loading blog post:', error);
    }
}

/**
 * Generate Table of Contents
 * (For blog post pages)
 */
function generateTableOfContents() {
    const content = document.querySelector('.blog-post-content');
    if (!content) return;

    const headings = content.querySelectorAll('h2, h3');
    if (headings.length === 0) return;

    const toc = document.createElement('div');
    toc.className = 'table-of-contents';
    toc.innerHTML = '<h3>Table of Contents</h3><ul></ul>';

    const tocList = toc.querySelector('ul');

    headings.forEach((heading, index) => {
        const id = `heading-${index}`;
        heading.id = id;

        const li = document.createElement('li');
        li.innerHTML = `<a href="#${id}">${heading.textContent}</a>`;

        if (heading.tagName === 'H3') {
            li.style.marginLeft = '1rem';
        }

        tocList.appendChild(li);
    });

    // Insert TOC before content
    content.parentElement.insertBefore(toc, content);
}

/**
 * Utility Functions
 */
function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Export functions for external use
window.blogUtils = {
    loadBlogArticles,
    loadBlogPost,
    calculateReadingTime,
    generateTableOfContents
};
