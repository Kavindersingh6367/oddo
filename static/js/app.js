/**
 * GlobeTrotter — Frontend Single Page Application
 * Production-quality state management, dynamic budgeting, travel intelligence, and Odoo REST API client.
 */

// ================= App State =================
const state = {
    user: null,
    token: localStorage.getItem('gt_token') || null,
    currentPage: 'dashboard',
    trips: [],
    currentTripId: null,
    currentTrip: null,
    destinations: [],
    activities: [],
    viewMode: 'builder', // 'builder' | 'calendar' | 'timeline' | 'presentation' | 'budget'
    sharedToken: null,
    sharedTrip: null,
    searchQuery: '',
    selectedRegion: 'all',
    selectedCategory: 'all'
};

// ================= API Client =================
async function apiRequest(endpoint, method = 'GET', body = null) {
    const headers = {
        'Content-Type': 'application/json'
    };
    if (state.token) {
        headers['Authorization'] = `Bearer ${state.token}`;
        headers['X-Session-Token'] = state.token;
    }

    const options = {
        method,
        headers
    };
    if (body && (method === 'POST' || method === 'PUT')) {
        options.body = JSON.stringify(body);
    }

    try {
        const response = await fetch(endpoint, options);
        const data = await response.json();
        if (!response.ok && !data.error) {
            throw new Error(`HTTP Error ${response.status}`);
        }
        return data;
    } catch (err) {
        console.error("API Request Error:", err);
        return { success: false, error: err.message || 'Network error' };
    }
}

// ================= Notification Toast Helper =================
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let icon = 'fa-check-circle';
    if (type === 'error') icon = 'fa-circle-exclamation';
    if (type === 'info') icon = 'fa-circle-info';

    toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${escapeHtml(message)}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function formatCurrency(amount, currency = 'INR') {
    const num = Number(amount) || 0;
    const symMap = {
        'INR': '₹',
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'JPY': '¥',
        'AED': 'AED ',
        'SGD': 'S$'
    };
    const sym = symMap[currency] || (currency + ' ');
    return `${sym}${num.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
}

function formatDateRange(start, end) {
    if (!start || !end) return 'Dates pending';
    try {
        const s = new Date(start);
        const e = new Date(end);
        const sStr = s.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        const eStr = e.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        return `${sStr} — ${eStr}`;
    } catch(err) {
        return `${start} — ${end}`;
    }
}

// ================= Authentication =================
async function initAuth() {
    if (state.token) {
        const res = await apiRequest('/api/v1/auth/me');
        if (res.success && res.user) {
            state.user = res.user;
        } else {
            state.token = null;
            localStorage.removeItem('gt_token');
        }
    }
    renderAuthNav();
}

function renderAuthNav() {
    const section = document.getElementById('auth-section');
    const adminNav = document.getElementById('nav-admin');
    
    if (adminNav) {
        adminNav.style.display = (state.user && state.user.role === 'admin') ? 'inline-flex' : 'none';
    }

    if (!section) return;

    if (state.user) {
        section.innerHTML = `
            <div class="auth-user-pill" onclick="openProfileModal()">
                <div class="user-avatar">${state.user.name.charAt(0).toUpperCase()}</div>
                <span class="user-name-tag">${escapeHtml(state.user.name.split(' ')[0])}</span>
                ${state.user.role === 'admin' ? '<span class="role-badge">Admin</span>' : ''}
            </div>
            <button class="btn btn-subtle btn-sm" onclick="handleLogout()" title="Log out">
                <i class="fa-solid fa-arrow-right-from-bracket"></i>
            </button>
        `;
    } else {
        section.innerHTML = `
            <button class="btn btn-outline btn-sm" onclick="openLoginModal()">Log In</button>
            <button class="btn btn-primary btn-sm" onclick="openSignupModal()">Sign Up</button>
        `;
    }
}

async function handleLogin(email, password) {
    const res = await apiRequest('/api/v1/auth/login', 'POST', { email, password });
    if (res.success) {
        state.token = res.token;
        state.user = res.user;
        localStorage.setItem('gt_token', res.token);
        closeModal();
        renderAuthNav();
        showToast(`Welcome back, ${state.user.name}!`);
        navigateTo('dashboard');
    } else {
        showToast(res.error || 'Login failed', 'error');
    }
}

async function handleDemoLogin(role = 'traveler') {
    const res = await apiRequest('/api/v1/auth/demo-login', 'POST', { role });
    if (res.success) {
        state.token = res.token;
        state.user = res.user;
        localStorage.setItem('gt_token', res.token);
        closeModal();
        renderAuthNav();
        showToast(`Signed in as demo ${role === 'admin' ? 'Administrator' : 'Traveler'}!`);
        navigateTo('dashboard');
    } else {
        showToast(res.error || 'Demo login failed', 'error');
    }
}

async function handleSignup(name, email, password, currency, travelStyle) {
    const res = await apiRequest('/api/v1/auth/signup', 'POST', {
        name, email, password, preferred_currency: currency, preferred_travel_style: travelStyle
    });
    if (res.success) {
        state.token = res.token;
        state.user = res.user;
        localStorage.setItem('gt_token', res.token);
        closeModal();
        renderAuthNav();
        showToast(`Welcome to GlobeTrotter, ${state.user.name}!`);
        navigateTo('dashboard');
    } else {
        showToast(res.error || 'Registration failed', 'error');
    }
}

async function handleLogout() {
    await apiRequest('/api/v1/auth/logout', 'POST');
    state.token = null;
    state.user = null;
    localStorage.removeItem('gt_token');
    renderAuthNav();
    showToast('Logged out successfully.');
    navigateTo('dashboard');
}

// ================= Navigation Routing =================
function navigateTo(page, param = null) {
    state.currentPage = page;
    
    // Update top nav active state
    document.querySelectorAll('.nav-item').forEach(el => {
        el.classList.toggle('active', el.dataset.page === page);
    });

    const main = document.getElementById('main-content');
    if (!main) return;

    if (page === 'dashboard') {
        renderDashboard();
    } else if (page === 'trips') {
        renderTripsList();
    } else if (page === 'itinerary') {
        if (param) state.currentTripId = param;
        renderItineraryBuilder();
    } else if (page === 'destinations') {
        renderDestinationsCatalog();
    } else if (page === 'activities') {
        renderActivitiesCatalog();
    } else if (page === 'admin') {
        renderAdminDashboard();
    } else if (page === 'shared') {
        if (param) state.sharedToken = param;
        renderPublicSharedTrip();
    }
}

// ================= View 1: Dashboard =================
async function renderDashboard() {
    const main = document.getElementById('main-content');
    main.innerHTML = `<div class="loading-state"><i class="fa-solid fa-spinner fa-spin"></i> Loading GlobeTrotter dashboard...</div>`;

    // Fetch user trips & destinations
    let trips = [];
    if (state.user) {
        const tRes = await apiRequest('/api/v1/trips');
        if (tRes.success) {
            trips = tRes.trips || [];
            state.trips = trips;
        }
    }

    const dRes = await apiRequest('/api/v1/destinations');
    const destinations = dRes.success ? (dRes.destinations || []) : [];
    state.destinations = destinations;

    // Calculate Dashboard KPIs
    const totalTrips = trips.length;
    const activeTrips = trips.filter(t => t.status === 'upcoming' || t.status === 'ongoing').length;
    const totalBudget = trips.reduce((sum, t) => sum + Number(t.total_budget || 0), 0);
    const upcomingTrip = trips.find(t => t.status === 'upcoming' || t.status === 'ongoing') || trips[0];

    const upcomingDest = (upcomingTrip && upcomingTrip.stops_count > 0) ? `${upcomingTrip.name}` : (trips.length > 0 ? trips[0].name : 'Rajasthan Explorer');

    let html = `
        <!-- Hero Section -->
        <div class="dashboard-hero">
            <div class="hero-content">
                <div class="hero-badge">
                    <i class="fa-solid fa-wand-magic-sparkles"></i> Personalized Itinerary Engine
                </div>
                <h1 class="hero-title">${state.user ? `Welcome back, ${escapeHtml(state.user.name.split(' ')[0])}!` : 'Design Your Perfect Journey with GlobeTrotter'}</h1>
                <p class="hero-desc">
                    Seamlessly assemble multi-city itineraries, discover curated activities, optimize trip budgets in real time, and share your adventures with a single click.
                </p>
                <div class="hero-actions">
                    <button class="btn btn-accent btn-lg btn-glow" onclick="openCreateTripModal()">
                        <i class="fa-solid fa-plus"></i> Plan New Trip
                    </button>
                    ${!state.user ? `
                        <button class="btn btn-outline btn-lg" onclick="handleDemoLogin('traveler')">
                            <i class="fa-solid fa-bolt"></i> 1-Click Demo Traveler
                        </button>
                        <button class="btn btn-subtle btn-lg" onclick="handleDemoLogin('admin')">
                            <i class="fa-solid fa-shield-halved"></i> 1-Click Admin Demo
                        </button>
                    ` : `
                        <button class="btn btn-outline btn-lg" onclick="navigateTo('destinations')">
                            <i class="fa-solid fa-compass"></i> Discover Destinations
                        </button>
                    `}
                </div>
            </div>
        </div>

        <!-- KPI Grid -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-icon-wrap indigo"><i class="fa-solid fa-suitcase-rolling"></i></div>
                <div class="kpi-data">
                    <span class="kpi-label">Total Itineraries</span>
                    <span class="kpi-val">${totalTrips}</span>
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-icon-wrap emerald"><i class="fa-solid fa-paper-plane"></i></div>
                <div class="kpi-data">
                    <span class="kpi-label">Active / Upcoming</span>
                    <span class="kpi-val">${activeTrips}</span>
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-icon-wrap amber"><i class="fa-solid fa-wallet"></i></div>
                <div class="kpi-data">
                    <span class="kpi-label">Total Trip Budgets</span>
                    <span class="kpi-val">${formatCurrency(totalBudget, state.user ? state.user.preferred_currency : 'INR')}</span>
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-icon-wrap sky"><i class="fa-solid fa-map-pin"></i></div>
                <div class="kpi-data">
                    <span class="kpi-label">Next Destination</span>
                    <span class="kpi-val" style="font-size: 1.25rem;">${escapeHtml(upcomingDest)}</span>
                </div>
            </div>
        </div>

        <!-- Recent Trips Section -->
        <div class="section-header">
            <h2 class="section-title"><i class="fa-solid fa-calendar-days" style="color: var(--primary);"></i> Your Travel Plans</h2>
            <div style="display: flex; gap: 0.5rem;">
                <button class="btn btn-outline btn-sm" onclick="navigateTo('trips')">View All Trips (${trips.length})</button>
                <button class="btn btn-primary btn-sm" onclick="openCreateTripModal()"><i class="fa-solid fa-plus"></i> New Trip</button>
            </div>
        </div>
    `;

    if (trips.length === 0) {
        html += `
            <div class="empty-state-box" style="background: #fff; border: 1px dashed var(--border-color); border-radius: var(--radius-lg); padding: 3rem; text-align: center; margin-bottom: 2.5rem;">
                <div style="font-size: 3rem; color: var(--primary); margin-bottom: 1rem;"><i class="fa-solid fa-map-location-dot"></i></div>
                <h3 style="margin-bottom: 0.5rem;">You haven't planned a trip yet.</h3>
                <p style="color: var(--text-muted); max-width: 480px; margin: 0 auto 1.5rem;">
                    Start your travel story! Choose your cities, assign dates, add activities, and watch your budget balance itself automatically.
                </p>
                <button class="btn btn-primary btn-lg" onclick="openCreateTripModal()">
                    <i class="fa-solid fa-plus"></i> Plan Your First Trip
                </button>
            </div>
        `;
    } else {
        html += `<div class="trip-grid">`;
        trips.slice(0, 6).forEach(trip => {
            const util = trip.budget_utilization || 0;
            let barClass = 'normal';
            if (util > 100) barClass = 'danger';
            else if (util >= 85) barClass = 'warning';

            html += `
                <div class="trip-card" onclick="navigateTo('itinerary', ${trip.id})">
                    <div class="trip-card-cover">
                        <img src="${trip.cover_image || 'https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=800&q=80'}" alt="${escapeHtml(trip.name)}" loading="lazy">
                        <span class="trip-status-tag ${trip.status}">${trip.status}</span>
                        <span class="trip-style-tag">${escapeHtml(trip.travel_style || 'Balanced')}</span>
                    </div>
                    <div class="trip-card-body">
                        <h3 class="trip-card-title">${escapeHtml(trip.name)}</h3>
                        <div class="trip-dates">
                            <i class="fa-regular fa-calendar"></i>
                            ${formatDateRange(trip.start_date, trip.end_date)} (${trip.duration_days} Days)
                        </div>
                        <div class="trip-meta-row">
                            <div class="trip-meta-item"><i class="fa-solid fa-city"></i> ${trip.stops_count || 0} Cities</div>
                            <div class="trip-meta-item"><i class="fa-solid fa-ticket"></i> ${trip.activities_count || 0} Acts</div>
                            <div class="trip-meta-item"><i class="fa-solid fa-users"></i> ${trip.travelers_count || 1}</div>
                        </div>
                        <div class="trip-budget-progress">
                            <div class="progress-header">
                                <span>Budget: ${formatCurrency(trip.total_budget, trip.currency)}</span>
                                <span>${util.toFixed(0)}%</span>
                            </div>
                            <div class="progress-bar-track">
                                <div class="progress-bar-fill ${barClass}" style="width: ${Math.min(100, util)}%;"></div>
                            </div>
                        </div>
                        <div class="trip-card-actions">
                            <span class="badge-chip score" title="Trip Balance Score">
                                <i class="fa-solid fa-gauge-high"></i> Score: ${trip.trip_balance_score || 75}/100
                            </span>
                            <span style="font-weight: 700; color: var(--primary); font-size: 0.88rem;">Open Plan &rarr;</span>
                        </div>
                    </div>
                </div>
            `;
        });
        html += `</div>`;
    }

    // Recommended Destinations Carousel
    html += `
        <div class="section-header" style="margin-top: 2rem;">
            <h2 class="section-title"><i class="fa-solid fa-fire" style="color: var(--accent);"></i> Trending Travel Destinations</h2>
            <button class="btn btn-outline btn-sm" onclick="navigateTo('destinations')">Explore All Destinations</button>
        </div>
        <div class="trip-grid">
    `;

    destinations.slice(0, 4).forEach(dest => {
        html += `
            <div class="trip-card" onclick="openDestinationDetailModal(${dest.id})">
                <div class="trip-card-cover">
                    <img src="${dest.cover_image}" alt="${escapeHtml(dest.name)}" loading="lazy">
                    <span class="trip-status-tag" style="background: rgba(15, 23, 42, 0.85); color: #FDBA74;">
                        <i class="fa-solid fa-star"></i> ${dest.popularity}/100
                    </span>
                    <span class="trip-style-tag">${escapeHtml(dest.country)}</span>
                </div>
                <div class="trip-card-body">
                    <h3 class="trip-card-title">${escapeHtml(dest.name)}, ${escapeHtml(dest.country)}</h3>
                    <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.75rem; line-height: 1.4;">
                        ${escapeHtml(dest.description.substring(0, 90))}...
                    </p>
                    <div class="trip-meta-row" style="margin-top: auto;">
                        <div class="trip-meta-item"><i class="fa-solid fa-clock"></i> Rec: ${dest.recommended_duration_days} Days</div>
                        <div class="trip-meta-item"><i class="fa-solid fa-coins"></i> Cost: ${'₹'.repeat(dest.cost_index || 2)}</div>
                    </div>
                    <div class="trip-card-actions">
                        <button class="btn btn-subtle btn-sm" onclick="event.stopPropagation(); openAddToTripModal(${dest.id})">
                            <i class="fa-solid fa-plus"></i> Add to Trip
                        </button>
                        <button class="btn btn-outline btn-sm" onclick="event.stopPropagation(); openDestinationDetailModal(${dest.id})">
                            View Activities
                        </button>
                    </div>
                </div>
            </div>
        `;
    });

    html += `</div>`;
    main.innerHTML = html;
}

// ================= View 2: My Trips List =================
async function renderTripsList(statusFilter = 'all') {
    const main = document.getElementById('main-content');
    if (!state.user) {
        main.innerHTML = `
            <div style="background: #fff; border-radius: var(--radius-lg); padding: 3rem; text-align: center; border: 1px solid var(--border-color);">
                <h2>Please log in to manage your itineraries</h2>
                <p style="color: var(--text-muted); margin: 0.75rem 0 1.5rem;">Track, budget, and share your multi-city journeys in one place.</p>
                <button class="btn btn-primary" onclick="openLoginModal()">Log In</button>
            </div>
        `;
        return;
    }

    main.innerHTML = `<div class="loading-state"><i class="fa-solid fa-spinner fa-spin"></i> Loading your itineraries...</div>`;
    const res = await apiRequest(`/api/v1/trips?status=${statusFilter}`);
    const trips = res.success ? (res.trips || []) : [];
    state.trips = trips;

    let html = `
        <div class="section-header">
            <div>
                <h1 style="font-size: 2rem;">My Itineraries</h1>
                <p style="color: var(--text-muted);">Manage, duplicate, and schedule your custom travel journeys.</p>
            </div>
            <button class="btn btn-primary" onclick="openCreateTripModal()">
                <i class="fa-solid fa-plus"></i> Plan New Trip
            </button>
        </div>

        <!-- Filter Tabs -->
        <div style="display: flex; gap: 0.5rem; margin-bottom: 1.5rem; flex-wrap: wrap;">
            <button class="btn btn-sm ${statusFilter === 'all' ? 'btn-primary' : 'btn-outline'}" onclick="renderTripsList('all')">All Trips</button>
            <button class="btn btn-sm ${statusFilter === 'upcoming' ? 'btn-primary' : 'btn-outline'}" onclick="renderTripsList('upcoming')">Upcoming</button>
            <button class="btn btn-sm ${statusFilter === 'ongoing' ? 'btn-primary' : 'btn-outline'}" onclick="renderTripsList('ongoing')">Ongoing</button>
            <button class="btn btn-sm ${statusFilter === 'completed' ? 'btn-primary' : 'btn-outline'}" onclick="renderTripsList('completed')">Completed</button>
            <button class="btn btn-sm ${statusFilter === 'draft' ? 'btn-primary' : 'btn-outline'}" onclick="renderTripsList('draft')">Drafts</button>
        </div>
    `;

    if (trips.length === 0) {
        html += `
            <div style="background: #fff; border: 1px dashed var(--border-color); border-radius: var(--radius-lg); padding: 3.5rem; text-align: center;">
                <i class="fa-solid fa-plane-slash" style="font-size: 3rem; color: var(--text-light); margin-bottom: 1rem;"></i>
                <h3>No itineraries found in this section</h3>
                <p style="color: var(--text-muted); margin-bottom: 1.5rem;">Create a trip to organize destinations, activities, and dynamic budgets.</p>
                <button class="btn btn-primary" onclick="openCreateTripModal()"><i class="fa-solid fa-plus"></i> Plan a Trip</button>
            </div>
        `;
    } else {
        html += `<div class="trip-grid">`;
        trips.forEach(trip => {
            const util = trip.budget_utilization || 0;
            let barClass = 'normal';
            if (util > 100) barClass = 'danger';
            else if (util >= 85) barClass = 'warning';

            html += `
                <div class="trip-card" onclick="navigateTo('itinerary', ${trip.id})">
                    <div class="trip-card-cover">
                        <img src="${trip.cover_image || 'https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=800&q=80'}" alt="${escapeHtml(trip.name)}" loading="lazy">
                        <span class="trip-status-tag ${trip.status}">${trip.status}</span>
                        <span class="trip-style-tag">${escapeHtml(trip.travel_style || 'Balanced')}</span>
                    </div>
                    <div class="trip-card-body">
                        <h3 class="trip-card-title">${escapeHtml(trip.name)}</h3>
                        <div class="trip-dates">
                            <i class="fa-regular fa-calendar"></i>
                            ${formatDateRange(trip.start_date, trip.end_date)} (${trip.duration_days} Days)
                        </div>
                        <div class="trip-meta-row">
                            <div class="trip-meta-item"><i class="fa-solid fa-city"></i> ${trip.stops_count || 0} Stops</div>
                            <div class="trip-meta-item"><i class="fa-solid fa-ticket"></i> ${trip.activities_count || 0} Acts</div>
                            <div class="trip-meta-item"><i class="fa-solid fa-users"></i> ${trip.travelers_count || 1}</div>
                        </div>
                        <div class="trip-budget-progress">
                            <div class="progress-header">
                                <span>Budget: ${formatCurrency(trip.total_budget, trip.currency)}</span>
                                <span>${util.toFixed(0)}%</span>
                            </div>
                            <div class="progress-bar-track">
                                <div class="progress-bar-fill ${barClass}" style="width: ${Math.min(100, util)}%;"></div>
                            </div>
                        </div>
                        <div class="trip-card-actions" onclick="event.stopPropagation();">
                            <div style="display: flex; gap: 0.35rem;">
                                <button class="btn btn-subtle btn-sm" onclick="handleDuplicateTrip(${trip.id})" title="Duplicate Itinerary"><i class="fa-regular fa-copy"></i></button>
                                <button class="btn btn-subtle btn-sm" onclick="openShareModal(${trip.id})" title="Share Itinerary"><i class="fa-solid fa-share-nodes"></i></button>
                                <button class="btn btn-danger-outline btn-sm" onclick="handleDeleteTrip(${trip.id})" title="Delete Itinerary"><i class="fa-regular fa-trash-can"></i></button>
                            </div>
                            <button class="btn btn-primary btn-sm" onclick="navigateTo('itinerary', ${trip.id})">Open Builder</button>
                        </div>
                    </div>
                </div>
            `;
        });
        html += `</div>`;
    }
    main.innerHTML = html;
}

// ================= View 3: Central Itinerary Builder =================
async function renderItineraryBuilder() {
    const main = document.getElementById('main-content');
    if (!state.currentTripId) {
        navigateTo('trips');
        return;
    }

    main.innerHTML = `<div class="loading-state"><i class="fa-solid fa-spinner fa-spin"></i> Loading full itinerary plan & intelligence...</div>`;

    const res = await apiRequest(`/api/v1/trips/${state.currentTripId}`);
    if (!res.success || !res.trip) {
        showToast(res.error || 'Failed to load trip', 'error');
        navigateTo('trips');
        return;
    }

    const trip = res.trip;
    state.currentTrip = trip;

    let html = `
        <!-- Itinerary Header Banner -->
        <div class="itinerary-header-banner">
            <div class="itinerary-top-row">
                <div class="itinerary-title-block">
                    <h1>${escapeHtml(trip.name)}</h1>
                    <div class="itinerary-chips-row">
                        <span class="badge-chip primary"><i class="fa-regular fa-calendar"></i> ${formatDateRange(trip.start_date, trip.end_date)} (${trip.duration_days} Days)</span>
                        <span class="badge-chip accent"><i class="fa-solid fa-users"></i> ${trip.travelers_count} Traveler${trip.travelers_count > 1 ? 's' : ''}</span>
                        <span class="badge-chip success"><i class="fa-solid fa-wallet"></i> Budget: ${formatCurrency(trip.total_budget, trip.currency)}</span>
                        <span class="badge-chip"><i class="fa-solid fa-compass"></i> Style: ${escapeHtml(trip.travel_style || 'Balanced')}</span>
                        <span class="badge-chip score"><i class="fa-solid fa-gauge-high"></i> Balance Score: ${trip.trip_balance_score}/100</span>
                    </div>
                </div>
                <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                    <button class="btn btn-outline btn-sm" onclick="openEditTripModal(${trip.id})"><i class="fa-solid fa-pen"></i> Edit Details</button>
                    <button class="btn btn-accent btn-sm" onclick="openShareModal(${trip.id})"><i class="fa-solid fa-share-nodes"></i> Share Publicly</button>
                    <button class="btn btn-subtle btn-sm" onclick="handleDuplicateTrip(${trip.id})"><i class="fa-regular fa-copy"></i> Duplicate</button>
                </div>
            </div>

            <!-- View Switcher Toolbar -->
            <div class="itinerary-actions-bar">
                <div style="display: flex; gap: 0.4rem; flex-wrap: wrap;">
                    <button class="btn btn-sm ${state.viewMode === 'builder' ? 'btn-primary' : 'btn-outline'}" onclick="switchItineraryView('builder')">
                        <i class="fa-solid fa-list-check"></i> Itinerary Builder
                    </button>
                    <button class="btn btn-sm ${state.viewMode === 'calendar' ? 'btn-primary' : 'btn-outline'}" onclick="switchItineraryView('calendar')">
                        <i class="fa-regular fa-calendar-days"></i> Calendar View
                    </button>
                    <button class="btn btn-sm ${state.viewMode === 'timeline' ? 'btn-primary' : 'btn-outline'}" onclick="switchItineraryView('timeline')">
                        <i class="fa-solid fa-route"></i> Timeline View
                    </button>
                    <button class="btn btn-sm ${state.viewMode === 'budget' ? 'btn-primary' : 'btn-outline'}" onclick="switchItineraryView('budget')">
                        <i class="fa-solid fa-chart-pie"></i> Budget &amp; Intelligence
                    </button>
                    <button class="btn btn-sm ${state.viewMode === 'presentation' ? 'btn-primary' : 'btn-outline'}" onclick="switchItineraryView('presentation')">
                        <i class="fa-solid fa-tv"></i> Presentation Mode
                    </button>
                </div>
                <div style="margin-left: auto; display: flex; gap: 0.5rem;">
                    <button class="btn btn-primary btn-sm" onclick="openAddStopModal(${trip.id})"><i class="fa-solid fa-location-dot"></i> + Add City Stop</button>
                    <button class="btn btn-outline btn-sm" onclick="openAddExpenseModal(${trip.id})"><i class="fa-solid fa-receipt"></i> + Add Expense</button>
                </div>
            </div>
        </div>
    `;

    // Render Sub-Views based on state.viewMode
    if (state.viewMode === 'builder') {
        html += renderBuilderScheduleView(trip);
    } else if (state.viewMode === 'calendar') {
        html += renderCalendarGridView(trip);
    } else if (state.viewMode === 'timeline') {
        html += renderVerticalTimelineView(trip);
    } else if (state.viewMode === 'budget') {
        html += renderBudgetAndIntelligenceView(trip);
    } else if (state.viewMode === 'presentation') {
        html += renderPresentationView(trip);
    }

    main.innerHTML = html;
}

function switchItineraryView(mode) {
    state.viewMode = mode;
    renderItineraryBuilder();
}

// ================= Builder Sub-View: Stops Rail + Day Schedule =================
function renderBuilderScheduleView(trip) {
    const stops = trip.stops || [];
    const activities = trip.activities || [];
    const durationDays = trip.duration_days || 1;

    let html = `
        <!-- Multi-City Stops Rail -->
        <div class="stops-rail-container">
            <div class="stops-rail-header">
                <div>
                    <h3 style="font-size: 1.15rem;"><i class="fa-solid fa-map-location-dot" style="color: var(--primary);"></i> Multi-City Route Sequence</h3>
                    <p style="font-size: 0.82rem; color: var(--text-muted);">Reorder stops to optimize travel route.</p>
                </div>
                <button class="btn btn-outline btn-sm" onclick="openAddStopModal(${trip.id})">
                    <i class="fa-solid fa-plus"></i> Add Destination
                </button>
            </div>
            <div class="stops-scroll-track">
    `;

    if (stops.length === 0) {
        html += `
            <div style="padding: 1.5rem; text-align: center; width: 100%; color: var(--text-muted);">
                <i class="fa-solid fa-location-dot" style="font-size: 1.5rem; margin-bottom: 0.5rem; color: var(--accent);"></i>
                <div>No destination stops added yet. Click <strong>+ Add Destination</strong> to start building your route.</div>
            </div>
        `;
    } else {
        stops.forEach((stop, index) => {
            html += `
                <div class="stop-sequence-card">
                    <span class="stop-seq-badge">${index + 1}</span>
                    <div class="stop-city-name">${escapeHtml(stop.city_name)}, ${escapeHtml(stop.country_name)}</div>
                    <div class="stop-dates-text">
                        <i class="fa-regular fa-calendar"></i> ${formatDateRange(stop.arrival_date, stop.departure_date)} (${stop.duration_days}d)
                    </div>
                    <div class="stop-card-controls">
                        <div style="display: flex; gap: 0.25rem;">
                            <button class="btn btn-subtle btn-sm" ${index === 0 ? 'disabled' : ''} onclick="handleMoveStop(${trip.id}, ${index}, -1)" title="Move Left"><i class="fa-solid fa-arrow-left"></i></button>
                            <button class="btn btn-subtle btn-sm" ${index === stops.length - 1 ? 'disabled' : ''} onclick="handleMoveStop(${trip.id}, ${index}, 1)" title="Move Right"><i class="fa-solid fa-arrow-right"></i></button>
                        </div>
                        <button class="btn btn-danger-outline btn-sm" onclick="handleDeleteStop(${trip.id}, ${stop.id})" title="Remove City"><i class="fa-regular fa-trash-can"></i></button>
                    </div>
                </div>
            `;
            if (index < stops.length - 1) {
                html += `<div class="stop-arrow-connector"><i class="fa-solid fa-arrow-right-long"></i></div>`;
            }
        });
    }

    html += `
            </div>
        </div>

        <!-- Day-Wise Schedule Blocks -->
        <div class="section-header">
            <h2 class="section-title"><i class="fa-solid fa-calendar-check" style="color: var(--primary);"></i> Day-Wise Schedule &amp; Activities</h2>
        </div>
    `;

    // Generate day blocks
    for (let dayNum = 1; dayNum <= durationDays; dayNum++) {
        // Calculate date of dayNum
        let dayDateStr = '';
        try {
            const d = new Date(trip.start_date);
            d.setDate(d.getDate() + (dayNum - 1));
            dayDateStr = d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
        } catch(e) {}

        // Filter activities for this day
        const dayActivities = activities.filter(a => Number(a.day_number) === dayNum);
        const dayCost = dayActivities.reduce((sum, a) => sum + Number(a.estimated_cost || 0), 0);

        html += `
            <div class="day-schedule-block">
                <div class="day-header">
                    <div class="day-header-left">
                        <span class="day-pill">DAY ${dayNum}</span>
                        <div class="day-title-text">${dayDateStr}</div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 1rem;">
                        <span style="font-weight: 700; font-size: 0.95rem; color: var(--text-muted);">
                            Daily Est: ${formatCurrency(dayCost, trip.currency)}
                        </span>
                        <button class="btn btn-primary btn-sm" onclick="openAddActivityModal(${trip.id}, ${dayNum})">
                            <i class="fa-solid fa-plus"></i> Add Activity
                        </button>
                    </div>
                </div>
                <div class="day-activities-list">
        `;

        if (dayActivities.length === 0) {
            html += `
                <div style="padding: 1.25rem; text-align: center; color: var(--text-muted); background: var(--bg-main); border-radius: var(--radius-md);">
                    <span>No activities scheduled for Day ${dayNum}. Click <strong>+ Add Activity</strong> to explore sightseeing, dining, and adventures.</span>
                </div>
            `;
        } else {
            dayActivities.forEach(act => {
                html += `
                    <div class="activity-item-card">
                        <div class="act-left-block">
                            <div class="act-time-badge">${escapeHtml(act.scheduled_time || '10:00')}</div>
                            <div class="act-details">
                                <span class="act-name">${escapeHtml(act.name)}</span>
                                <div class="act-meta-tags">
                                    <span class="category-tag ${act.category || 'sightseeing'}">${escapeHtml(act.category || 'sightseeing')}</span>
                                    <span><i class="fa-regular fa-clock"></i> ${act.duration_hours || 2}h</span>
                                    ${act.city_name ? `<span><i class="fa-solid fa-location-dot"></i> ${escapeHtml(act.city_name)}</span>` : ''}
                                </div>
                            </div>
                        </div>
                        <div style="display: flex; align-items: center; gap: 1.25rem;">
                            <div class="act-cost-badge">${formatCurrency(act.estimated_cost, trip.currency)}</div>
                            <div style="display: flex; gap: 0.35rem;">
                                <button class="btn btn-subtle btn-sm" onclick="openEditActivityModal(${trip.id}, ${act.id})" title="Edit"><i class="fa-solid fa-pen"></i></button>
                                <button class="btn btn-danger-outline btn-sm" onclick="handleDeleteActivity(${trip.id}, ${act.id})" title="Delete"><i class="fa-regular fa-trash-can"></i></button>
                            </div>
                        </div>
                    </div>
                `;
            });
        }

        html += `
                </div>
            </div>
        `;
    }

    return html;
}

// ================= Builder Sub-View: Budget & Intelligence Engine =================
function renderBudgetAndIntelligenceView(trip) {
    const bd = trip.category_breakdown || {};
    const alerts = trip.budget_intelligence_alerts || [];
    const factors = trip.balance_score_summary || [];
    const expenses = trip.expenses || [];
    const util = trip.budget_utilization || 0;

    let html = `
        <!-- Travel Balance Score Gauge -->
        <div class="balance-score-container">
            <div class="score-gauge-box" style="--score-pct: ${trip.trip_balance_score || 80};">
                <span class="score-number">${trip.trip_balance_score || 80}</span>
                <span class="score-max">OUT OF 100</span>
            </div>
            <div style="flex: 1;">
                <h2 style="color: #fff; margin-bottom: 0.35rem; font-size: 1.6rem;">Trip Balance &amp; Pacing Score</h2>
                <p style="color: #C7D2FE; font-size: 0.9rem; margin-bottom: 1.25rem;">
                    Our transparent rating engine evaluates budget alignment, activity density, city dwell time, and logistic completeness.
                </p>
                <div class="score-factors-grid">
    `;

    factors.forEach(f => {
        html += `
            <div class="factor-item">
                <div class="factor-header">
                    <span>${escapeHtml(f.name)}</span>
                    <span style="color: #FDBA74;">${f.score}/${f.max}</span>
                </div>
                <div class="factor-desc">${escapeHtml(f.description)}</div>
            </div>
        `;
    });

    html += `
                </div>
            </div>
        </div>

        <!-- Budget & Financial Intelligence Panel -->
        <div class="budget-intelligence-panel">
            <div class="section-header">
                <div>
                    <h2 class="section-title"><i class="fa-solid fa-calculator" style="color: var(--primary);"></i> Dynamic Budget Intelligence Engine</h2>
                    <p style="font-size: 0.85rem; color: var(--text-muted);">Real-time cost rollup across activities, accommodations, flights, and logistics.</p>
                </div>
                <button class="btn btn-primary btn-sm" onclick="openAddExpenseModal(${trip.id})">
                    <i class="fa-solid fa-receipt"></i> + Add Expense Item
                </button>
            </div>

            <!-- Financial KPIs -->
            <div class="budget-stats-grid">
                <div class="budget-metric-box">
                    <div class="label">Target Budget</div>
                    <div class="value" style="color: var(--primary);">${formatCurrency(trip.total_budget, trip.currency)}</div>
                </div>
                <div class="budget-metric-box">
                    <div class="label">Total Estimated</div>
                    <div class="value" style="color: ${trip.total_estimated_cost > trip.total_budget ? 'var(--danger)' : 'var(--text-main)'};">${formatCurrency(trip.total_estimated_cost, trip.currency)}</div>
                </div>
                <div class="budget-metric-box">
                    <div class="label">Remaining Budget</div>
                    <div class="value" style="color: ${trip.remaining_budget < 0 ? 'var(--danger)' : 'var(--success)'};">${formatCurrency(trip.remaining_budget, trip.currency)}</div>
                </div>
                <div class="budget-metric-box">
                    <div class="label">Per Traveler</div>
                    <div class="value">${formatCurrency(trip.cost_per_traveler, trip.currency)}</div>
                </div>
                <div class="budget-metric-box">
                    <div class="label">Per Day</div>
                    <div class="value">${formatCurrency(trip.cost_per_day, trip.currency)}</div>
                </div>
                <div class="budget-metric-box">
                    <div class="label">Utilization</div>
                    <div class="value" style="color: ${util > 100 ? 'var(--danger)' : 'var(--accent)'};">${util.toFixed(0)}%</div>
                </div>
            </div>

            <!-- Rule-Based Intelligence Alerts -->
            <div style="margin-bottom: 2rem;">
                <h4 style="margin-bottom: 0.75rem; font-size: 1.05rem;">Intelligence Insights &amp; Pacing Warnings</h4>
    `;

    if (alerts.length === 0) {
        html += `
            <div class="intelligence-alert success">
                <i class="fa-solid fa-circle-check"></i>
                <div><strong>Healthy Itinerary:</strong> Your schedule and expenses are currently balanced and within budget parameters.</div>
            </div>
        `;
    } else {
        alerts.forEach(a => {
            let icon = 'fa-circle-info';
            if (a.type === 'warning') icon = 'fa-triangle-exclamation';
            if (a.type === 'success') icon = 'fa-circle-check';

            html += `
                <div class="intelligence-alert ${a.type}">
                    <i class="fa-solid ${icon}"></i>
                    <div>
                        <strong>${escapeHtml(a.title)}:</strong> ${escapeHtml(a.message)}
                    </div>
                </div>
            `;
        });
    }

    html += `
            </div>

            <!-- Category Cost Breakdown -->
            <div style="margin-bottom: 2rem;">
                <h4 style="margin-bottom: 1rem; font-size: 1.05rem;">Cost Allocation by Category</h4>
                <div style="display: flex; flex-direction: column; gap: 0.85rem;">
    `;

    const totalCost = trip.total_estimated_cost || 1;
    const catList = [
        { key: 'activities', label: 'Activities & Experiences', icon: 'fa-ticket', color: '#4F46E5', amount: bd.activities || 0 },
        { key: 'accommodation', label: 'Accommodation & Lodging', icon: 'fa-hotel', color: '#F97316', amount: bd.accommodation || 0 },
        { key: 'transportation', label: 'Transportation & Flights', icon: 'fa-plane', color: '#0EA5E9', amount: bd.transportation || 0 },
        { key: 'food', label: 'Food & Dining', icon: 'fa-utensils', color: '#10B981', amount: bd.food || 0 },
        { key: 'miscellaneous', label: 'Miscellaneous & Shopping', icon: 'fa-bag-shopping', color: '#8B5CF6', amount: bd.miscellaneous || 0 }
    ];

    catList.forEach(c => {
        const pct = ((c.amount / totalCost) * 100) || 0;
        html += `
            <div>
                <div style="display: flex; justify-content: space-between; font-size: 0.88rem; font-weight: 600; margin-bottom: 0.35rem;">
                    <span><i class="fa-solid ${c.icon}" style="color: ${c.color}; margin-right: 0.4rem;"></i> ${c.label}</span>
                    <span>${formatCurrency(c.amount, trip.currency)} (${pct.toFixed(0)}%)</span>
                </div>
                <div class="progress-bar-track">
                    <div class="progress-bar-fill" style="width: ${pct}%; background: ${c.color};"></div>
                </div>
            </div>
        `;
    });

    html += `
                </div>
            </div>

            <!-- Expenses List Table -->
            <div>
                <div class="section-header">
                    <h4 style="font-size: 1.05rem;">Recorded Logistics &amp; Expenses</h4>
                </div>
    `;

    if (expenses.length === 0) {
        html += `
            <div style="padding: 1.5rem; text-align: center; color: var(--text-muted); background: var(--bg-main); border-radius: var(--radius-md);">
                No standalone expenses added yet. Click <strong>+ Add Expense Item</strong> to log hotel bookings, flights, and meals.
            </div>
        `;
    } else {
        html += `
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
        `;
        expenses.forEach(e => {
            html += `
                <div style="background: var(--bg-main); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 0.85rem 1.25rem; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-weight: 700; font-size: 0.95rem;">${escapeHtml(e.name)}</div>
                        <div style="font-size: 0.8rem; color: var(--text-muted); display: flex; gap: 0.75rem; margin-top: 0.15rem;">
                            <span class="category-tag ${e.category}">${escapeHtml(e.category)}</span>
                            ${e.date ? `<span><i class="fa-regular fa-calendar"></i> ${e.date}</span>` : ''}
                            ${e.notes ? `<span>${escapeHtml(e.notes)}</span>` : ''}
                        </div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 1rem;">
                        <span style="font-family: var(--font-heading); font-weight: 700; font-size: 1.05rem;">${formatCurrency(e.amount, trip.currency)}</span>
                        <button class="btn btn-danger-outline btn-sm" onclick="handleDeleteExpense(${trip.id}, ${e.id})"><i class="fa-regular fa-trash-can"></i></button>
                    </div>
                </div>
            `;
        });
        html += `</div>`;
    }

    html += `
            </div>
        </div>
    `;

    return html;
}

// ================= Builder Sub-View: Calendar Grid =================
function renderCalendarGridView(trip) {
    const activities = trip.activities || [];
    const durationDays = trip.duration_days || 1;

    let html = `
        <div class="calendar-view-container">
            <div class="section-header">
                <div>
                    <h2 class="section-title"><i class="fa-regular fa-calendar-days" style="color: var(--primary);"></i> Calendar Schedule Grid</h2>
                    <p style="font-size: 0.85rem; color: var(--text-muted);">Visual day-by-day itinerary mapping.</p>
                </div>
            </div>
            <div class="calendar-grid">
    `;

    for (let dayNum = 1; dayNum <= durationDays; dayNum++) {
        let dayDateStr = '';
        try {
            const d = new Date(trip.start_date);
            d.setDate(d.getDate() + (dayNum - 1));
            dayDateStr = d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
        } catch(e) {}

        const dayActs = activities.filter(a => Number(a.day_number) === dayNum);
        const dayCost = dayActs.reduce((sum, a) => sum + Number(a.estimated_cost || 0), 0);

        html += `
            <div class="calendar-day-cell">
                <div class="cal-day-title">
                    <span>Day ${dayNum}</span>
                    <span style="font-size: 0.75rem; color: var(--text-muted); font-weight: 500;">${dayDateStr}</span>
                </div>
                <div style="flex: 1; overflow-y: auto;">
        `;

        if (dayActs.length === 0) {
            html += `<div style="font-size: 0.78rem; color: var(--text-light); text-align: center; margin-top: 2rem;">No events</div>`;
        } else {
            dayActs.forEach(a => {
                html += `
                    <div class="cal-act-pill" title="${escapeHtml(a.name)}">
                        <span><strong>${escapeHtml(a.scheduled_time || '10:00')}</strong> ${escapeHtml(a.name.substring(0, 16))}...</span>
                        <span style="color: var(--primary);">${formatCurrency(a.estimated_cost, trip.currency)}</span>
                    </div>
                `;
            });
        }

        html += `
                </div>
                <div style="margin-top: auto; padding-top: 0.5rem; border-top: 1px dashed var(--border-color); font-size: 0.78rem; font-weight: 700; display: flex; justify-content: space-between;">
                    <span>Total:</span>
                    <span>${formatCurrency(dayCost, trip.currency)}</span>
                </div>
            </div>
        `;
    }

    html += `
            </div>
        </div>
    `;
    return html;
}

// ================= Builder Sub-View: Vertical Timeline =================
function renderVerticalTimelineView(trip) {
    const stops = trip.stops || [];
    const activities = trip.activities || [];
    const durationDays = trip.duration_days || 1;

    let html = `
        <div class="calendar-view-container">
            <div class="section-header">
                <div>
                    <h2 class="section-title"><i class="fa-solid fa-route" style="color: var(--primary);"></i> Journey Progression Timeline</h2>
                    <p style="font-size: 0.85rem; color: var(--text-muted);">Step-by-step traveler journey sequence.</p>
                </div>
            </div>
            <div class="timeline-container">
    `;

    for (let dayNum = 1; dayNum <= durationDays; dayNum++) {
        let dayDateStr = '';
        try {
            const d = new Date(trip.start_date);
            d.setDate(d.getDate() + (dayNum - 1));
            dayDateStr = d.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' });
        } catch(e) {}

        const dayActs = activities.filter(a => Number(a.day_number) === dayNum);

        html += `
            <div class="timeline-node">
                <div class="timeline-dot"><i class="fa-solid fa-flag"></i></div>
                <div style="background: var(--bg-main); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 1.25rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.85rem;">
                        <span class="day-pill">DAY ${dayNum}</span>
                        <span style="font-weight: 700; color: var(--text-main); font-size: 0.95rem;">${dayDateStr}</span>
                    </div>
        `;

        if (dayActs.length === 0) {
            html += `<p style="font-size: 0.85rem; color: var(--text-muted);">Leisure day / Transit</p>`;
        } else {
            html += `<div style="display: flex; flex-direction: column; gap: 0.65rem;">`;
            dayActs.forEach(a => {
                html += `
                    <div style="background: #fff; border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 0.85rem 1rem; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-weight: 700; color: var(--primary); margin-right: 0.5rem;">${escapeHtml(a.scheduled_time || '10:00')}</span>
                            <span style="font-weight: 600;">${escapeHtml(a.name)}</span>
                            <span class="category-tag ${a.category}" style="margin-left: 0.5rem;">${escapeHtml(a.category)}</span>
                        </div>
                        <span style="font-weight: 700; font-family: var(--font-heading);">${formatCurrency(a.estimated_cost, trip.currency)}</span>
                    </div>
                `;
            });
            html += `</div>`;
        }

        html += `
                </div>
            </div>
        `;
    }

    html += `
            </div>
        </div>
    `;
    return html;
}

// ================= Builder Sub-View: Presentation Mode =================
function renderPresentationView(trip) {
    const stops = trip.stops || [];
    const activities = trip.activities || [];
    const durationDays = trip.duration_days || 1;

    let html = `
        <div style="background: #fff; border: 1px solid var(--border-color); border-radius: var(--radius-xl); overflow: hidden; box-shadow: var(--shadow-xl); margin-bottom: 2rem;">
            <!-- Hero Banner -->
            <div style="height: 300px; position: relative; background: #1E1B4B;">
                <img src="${trip.cover_image || 'https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=1200&q=80'}" style="width: 100%; height: 100%; object-fit: cover; opacity: 0.75;">
                <div style="position: absolute; bottom: 0; left: 0; right: 0; padding: 2rem; background: linear-gradient(to top, rgba(15, 23, 42, 0.95), transparent); color: #fff;">
                    <div style="display: flex; gap: 0.5rem; margin-bottom: 0.5rem;">
                        <span class="badge-chip accent">${trip.travel_style || 'Balanced'}</span>
                        <span class="badge-chip score"><i class="fa-solid fa-star"></i> Score: ${trip.trip_balance_score}/100</span>
                    </div>
                    <h1 style="color: #fff; font-size: 2.4rem; margin-bottom: 0.4rem;">${escapeHtml(trip.name)}</h1>
                    <div style="color: #C7D2FE; font-size: 1rem; display: flex; gap: 1.5rem; flex-wrap: wrap;">
                        <span><i class="fa-regular fa-calendar"></i> ${formatDateRange(trip.start_date, trip.end_date)} (${trip.duration_days} Days)</span>
                        <span><i class="fa-solid fa-users"></i> ${trip.travelers_count} Travelers</span>
                        <span><i class="fa-solid fa-wallet"></i> Est. Cost: ${formatCurrency(trip.total_estimated_cost, trip.currency)}</span>
                    </div>
                </div>
            </div>

            <!-- Route Summary -->
            <div style="padding: 2rem; border-bottom: 1px solid var(--border-color); background: var(--bg-main);">
                <h3 style="margin-bottom: 1rem; font-size: 1.2rem;"><i class="fa-solid fa-map-pin" style="color: var(--primary);"></i> Route Overview</h3>
                <div style="display: flex; align-items: center; gap: 1rem; flex-wrap: wrap;">
    `;

    stops.forEach((s, idx) => {
        html += `
            <div style="background: #fff; border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 0.75rem 1.25rem; font-weight: 700;">
                ${idx + 1}. ${escapeHtml(s.city_name)}, ${escapeHtml(s.country_name)} (${s.duration_days}d)
            </div>
        `;
        if (idx < stops.length - 1) {
            html += `<i class="fa-solid fa-arrow-right" style="color: var(--primary);"></i>`;
        }
    });

    html += `
                </div>
            </div>

            <!-- Day-by-Day Showcase -->
            <div style="padding: 2rem;">
                <h3 style="margin-bottom: 1.5rem; font-size: 1.3rem;">Complete Day-by-Day Itinerary</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem;">
    `;

    for (let dayNum = 1; dayNum <= durationDays; dayNum++) {
        const dayActs = activities.filter(a => Number(a.day_number) === dayNum);
        let dayDateStr = '';
        try {
            const d = new Date(trip.start_date);
            d.setDate(d.getDate() + (dayNum - 1));
            dayDateStr = d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
        } catch(e) {}

        html += `
            <div style="background: var(--bg-main); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 1.25rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.85rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem;">
                    <span class="day-pill">DAY ${dayNum}</span>
                    <span style="font-size: 0.85rem; font-weight: 600; color: var(--text-muted);">${dayDateStr}</span>
                </div>
        `;

        if (dayActs.length === 0) {
            html += `<p style="font-size: 0.85rem; color: var(--text-light); text-align: center; padding: 1rem 0;">Free exploration day</p>`;
        } else {
            dayActs.forEach(a => {
                html += `
                    <div style="margin-bottom: 0.65rem; font-size: 0.88rem;">
                        <span style="font-weight: 700; color: var(--primary);">${escapeHtml(a.scheduled_time || '10:00')}</span> — 
                        <span style="font-weight: 600;">${escapeHtml(a.name)}</span>
                        <div style="font-size: 0.78rem; color: var(--text-muted);">${formatCurrency(a.estimated_cost, trip.currency)} &bull; ${escapeHtml(a.category)}</div>
                    </div>
                `;
            });
        }

        html += `</div>`;
    }

    html += `
                </div>
            </div>
        </div>
    `;

    return html;
}

// ================= View 4: Public Shared Trip Viewer =================
async function renderPublicSharedTrip() {
    const main = document.getElementById('main-content');
    if (!state.sharedToken) {
        // extract from URL if format is /shared/<token>
        const pathParts = window.location.pathname.split('/');
        if (pathParts[1] === 'shared' && pathParts[2]) {
            state.sharedToken = pathParts[2];
        }
    }

    if (!state.sharedToken) {
        navigateTo('dashboard');
        return;
    }

    main.innerHTML = `<div class="loading-state"><i class="fa-solid fa-spinner fa-spin"></i> Loading shared itinerary...</div>`;
    const res = await apiRequest(`/api/v1/shared/${state.sharedToken}`);
    if (!res.success || !res.trip) {
        main.innerHTML = `
            <div style="background: #fff; border-radius: var(--radius-lg); padding: 3rem; text-align: center; border: 1px solid var(--border-color);">
                <i class="fa-solid fa-link-slash" style="font-size: 3rem; color: var(--danger); margin-bottom: 1rem;"></i>
                <h2>Itinerary Not Available</h2>
                <p style="color: var(--text-muted); margin: 0.5rem 0 1.5rem;">This public link is either invalid, expired, or was made private by the author.</p>
                <button class="btn btn-primary" onclick="navigateTo('dashboard')">Go to GlobeTrotter Home</button>
            </div>
        `;
        return;
    }

    const trip = res.trip;
    state.sharedTrip = trip;

    let html = `
        <div style="background: #fff; border: 1px solid var(--border-color); border-radius: var(--radius-xl); overflow: hidden; box-shadow: var(--shadow-xl); margin-bottom: 2rem;">
            <!-- Top Callout Banner -->
            <div style="background: linear-gradient(135deg, #1E1B4B 0%, #4338CA 100%); color: #fff; padding: 1.25rem 2rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem;">
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <i class="fa-solid fa-share-nodes" style="font-size: 1.3rem; color: #FDBA74;"></i>
                    <div>
                        <div style="font-weight: 700;">Shared Itinerary by ${escapeHtml(trip.owner_name || 'GlobeTrotter Traveler')}</div>
                        <div style="font-size: 0.8rem; color: #C7D2FE;">You can copy this complete trip plan directly into your account.</div>
                    </div>
                </div>
                <button class="btn btn-accent btn-glow" onclick="handleCopySharedTrip('${state.sharedToken}')">
                    <i class="fa-solid fa-copy"></i> Copy Trip to My Account
                </button>
            </div>

            <!-- Hero Section -->
            <div style="height: 280px; position: relative;">
                <img src="${trip.cover_image || 'https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=1200&q=80'}" style="width: 100%; height: 100%; object-fit: cover;">
                <div style="position: absolute; bottom: 0; left: 0; right: 0; padding: 2rem; background: linear-gradient(to top, rgba(15, 23, 42, 0.9), transparent); color: #fff;">
                    <h1 style="color: #fff; font-size: 2.2rem; margin-bottom: 0.3rem;">${escapeHtml(trip.name)}</h1>
                    <div style="color: #C7D2FE; font-size: 0.95rem; display: flex; gap: 1.5rem; flex-wrap: wrap;">
                        <span><i class="fa-regular fa-calendar"></i> ${formatDateRange(trip.start_date, trip.end_date)} (${trip.duration_days} Days)</span>
                        <span><i class="fa-solid fa-users"></i> ${trip.travelers_count} Traveler(s)</span>
                        ${trip.total_budget > 0 ? `<span><i class="fa-solid fa-wallet"></i> Budget: ${formatCurrency(trip.total_budget, trip.currency)}</span>` : ''}
                    </div>
                </div>
            </div>

            <!-- Day-by-Day Breakdown -->
            <div style="padding: 2rem;">
                <h3 style="margin-bottom: 1.5rem; font-size: 1.3rem;"><i class="fa-solid fa-calendar-check" style="color: var(--primary);"></i> Trip Itinerary Schedule</h3>
                <div style="display: flex; flex-direction: column; gap: 1.25rem;">
    `;

    for (let dayNum = 1; dayNum <= (trip.duration_days || 1); dayNum++) {
        const dayActs = (trip.activities || []).filter(a => Number(a.day_number) === dayNum);

        html += `
            <div style="background: var(--bg-main); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 1.25rem;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem;">
                    <span class="day-pill">DAY ${dayNum}</span>
                </div>
        `;

        if (dayActs.length === 0) {
            html += `<p style="font-size: 0.85rem; color: var(--text-muted);">Free leisure day</p>`;
        } else {
            dayActs.forEach(a => {
                html += `
                    <div style="background: #fff; border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 0.75rem 1rem; margin-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-weight: 700; color: var(--primary); margin-right: 0.5rem;">${escapeHtml(a.scheduled_time || '10:00')}</span>
                            <span style="font-weight: 600;">${escapeHtml(a.name)}</span>
                            <span class="category-tag ${a.category}" style="margin-left: 0.5rem;">${escapeHtml(a.category)}</span>
                        </div>
                        ${a.estimated_cost > 0 ? `<span style="font-weight: 700;">${formatCurrency(a.estimated_cost, trip.currency)}</span>` : ''}
                    </div>
                `;
            });
        }

        html += `</div>`;
    }

    html += `
                </div>
            </div>
        </div>
    `;

    main.innerHTML = html;
}

// ================= View 5: Destinations Discovery =================
async function renderDestinationsCatalog() {
    const main = document.getElementById('main-content');
    main.innerHTML = `<div class="loading-state"><i class="fa-solid fa-spinner fa-spin"></i> Loading destination catalog...</div>`;

    const res = await apiRequest(`/api/v1/destinations?q=${encodeURIComponent(state.searchQuery)}&region=${state.selectedRegion}`);
    const destinations = res.success ? (res.destinations || []) : [];
    state.destinations = destinations;

    let html = `
        <div class="section-header">
            <div>
                <h1 style="font-size: 2rem;">Explore Destinations</h1>
                <p style="color: var(--text-muted);">Discover top world destinations, curated activities, and estimated cost indexes.</p>
            </div>
        </div>

        <!-- Search and Region Filters -->
        <div style="background: #fff; border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 1.25rem; margin-bottom: 2rem; display: flex; gap: 1rem; flex-wrap: wrap; align-items: center;">
            <div style="flex: 1; min-width: 260px; position: relative;">
                <input type="text" id="dest-search-input" class="form-control" placeholder="Search cities, countries (e.g. Jaipur, France, Tokyo)..." value="${escapeHtml(state.searchQuery)}" onkeyup="handleDestSearch(event)">
            </div>
            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                <button class="btn btn-sm ${state.selectedRegion === 'all' ? 'btn-primary' : 'btn-outline'}" onclick="filterDestRegion('all')">All Regions</button>
                <button class="btn btn-sm ${state.selectedRegion === 'asia' ? 'btn-primary' : 'btn-outline'}" onclick="filterDestRegion('asia')">Asia</button>
                <button class="btn btn-sm ${state.selectedRegion === 'europe' ? 'btn-primary' : 'btn-outline'}" onclick="filterDestRegion('europe')">Europe</button>
                <button class="btn btn-sm ${state.selectedRegion === 'middle_east' ? 'btn-primary' : 'btn-outline'}" onclick="filterDestRegion('middle_east')">Middle East</button>
            </div>
        </div>

        <div class="trip-grid">
    `;

    if (destinations.length === 0) {
        html += `
            <div style="grid-column: 1 / -1; padding: 3rem; text-align: center; background: #fff; border-radius: var(--radius-lg); border: 1px dashed var(--border-color);">
                <h3>No destinations matched your criteria.</h3>
                <p style="color: var(--text-muted); margin-top: 0.5rem;">Try searching for another city or country name.</p>
            </div>
        `;
    } else {
        destinations.forEach(dest => {
            html += `
                <div class="trip-card" onclick="openDestinationDetailModal(${dest.id})">
                    <div class="trip-card-cover">
                        <img src="${dest.cover_image}" alt="${escapeHtml(dest.name)}" loading="lazy">
                        <span class="trip-status-tag" style="background: rgba(15, 23, 42, 0.85); color: #FDBA74;">
                            <i class="fa-solid fa-star"></i> ${dest.popularity}/100
                        </span>
                        <span class="trip-style-tag">${escapeHtml(dest.country)}</span>
                    </div>
                    <div class="trip-card-body">
                        <h3 class="trip-card-title">${escapeHtml(dest.name)}, ${escapeHtml(dest.country)}</h3>
                        <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.75rem; line-height: 1.4;">
                            ${escapeHtml(dest.description.substring(0, 110))}...
                        </p>
                        <div class="trip-meta-row" style="margin-top: auto;">
                            <div class="trip-meta-item"><i class="fa-solid fa-clock"></i> Rec: ${dest.recommended_duration_days} Days</div>
                            <div class="trip-meta-item"><i class="fa-solid fa-coins"></i> Cost Index: ${'₹'.repeat(dest.cost_index || 2)}</div>
                            <div class="trip-meta-item"><i class="fa-solid fa-ticket"></i> ${dest.activity_count || 0} Acts</div>
                        </div>
                        <div class="trip-card-actions">
                            <button class="btn btn-primary btn-sm" onclick="event.stopPropagation(); openAddToTripModal(${dest.id})">
                                <i class="fa-solid fa-plus"></i> Add to My Trip
                            </button>
                            <button class="btn btn-outline btn-sm" onclick="event.stopPropagation(); openDestinationDetailModal(${dest.id})">
                                Details &amp; Experiences
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });
    }

    html += `</div>`;
    main.innerHTML = html;
}

function handleDestSearch(e) {
    state.searchQuery = e.target.value;
    if (e.key === 'Enter') {
        renderDestinationsCatalog();
    }
}

function filterDestRegion(region) {
    state.selectedRegion = region;
    renderDestinationsCatalog();
}

// ================= View 6: Activities Catalog =================
async function renderActivitiesCatalog() {
    const main = document.getElementById('main-content');
    main.innerHTML = `<div class="loading-state"><i class="fa-solid fa-spinner fa-spin"></i> Loading experiences &amp; activities...</div>`;

    const res = await apiRequest(`/api/v1/activities?category=${state.selectedCategory}`);
    const activities = res.success ? (res.activities || []) : [];
    state.activities = activities;

    let html = `
        <div class="section-header">
            <div>
                <h1 style="font-size: 2rem;">Experiences &amp; Activities</h1>
                <p style="color: var(--text-muted);">Browse curated things to do, tours, gastronomy, and cultural adventures.</p>
            </div>
        </div>

        <!-- Category Filters -->
        <div style="display: flex; gap: 0.4rem; margin-bottom: 2rem; flex-wrap: wrap;">
            <button class="btn btn-sm ${state.selectedCategory === 'all' ? 'btn-primary' : 'btn-outline'}" onclick="filterActivityCat('all')">All Categories</button>
            <button class="btn btn-sm ${state.selectedCategory === 'sightseeing' ? 'btn-primary' : 'btn-outline'}" onclick="filterActivityCat('sightseeing')">Sightseeing</button>
            <button class="btn btn-sm ${state.selectedCategory === 'food' ? 'btn-primary' : 'btn-outline'}" onclick="filterActivityCat('food')">Food &amp; Dining</button>
            <button class="btn btn-sm ${state.selectedCategory === 'culture' ? 'btn-primary' : 'btn-outline'}" onclick="filterActivityCat('culture')">Culture</button>
            <button class="btn btn-sm ${state.selectedCategory === 'adventure' ? 'btn-primary' : 'btn-outline'}" onclick="filterActivityCat('adventure')">Adventure</button>
            <button class="btn btn-sm ${state.selectedCategory === 'nature' ? 'btn-primary' : 'btn-outline'}" onclick="filterActivityCat('nature')">Nature</button>
            <button class="btn btn-sm ${state.selectedCategory === 'relaxation' ? 'btn-primary' : 'btn-outline'}" onclick="filterActivityCat('relaxation')">Relaxation</button>
        </div>

        <div class="trip-grid">
    `;

    activities.forEach(act => {
        html += `
            <div class="trip-card">
                <div class="trip-card-cover" style="height: 150px;">
                    <img src="${act.image || 'https://images.unsplash.com/photo-1598324789736-4861f89564a0?auto=format&fit=crop&w=800&q=80'}" alt="${escapeHtml(act.name)}" loading="lazy">
                    <span class="trip-status-tag ${act.category}">${escapeHtml(act.category)}</span>
                </div>
                <div class="trip-card-body">
                    <h3 class="trip-card-title">${escapeHtml(act.name)}</h3>
                    <div style="font-size: 0.82rem; color: var(--text-muted); margin-bottom: 0.5rem;">
                        <i class="fa-solid fa-location-dot"></i> ${escapeHtml(act.city_name)}, ${escapeHtml(act.country_name)}
                    </div>
                    <p style="font-size: 0.84rem; color: var(--text-muted); margin-bottom: 0.75rem; line-height: 1.4;">
                        ${escapeHtml(act.description)}
                    </p>
                    <div class="trip-meta-row" style="margin-top: auto;">
                        <div class="trip-meta-item"><i class="fa-regular fa-clock"></i> ${act.duration_hours}h</div>
                        <div class="trip-meta-item"><i class="fa-solid fa-star" style="color: #F59E0B;"></i> ${act.popularity}/100</div>
                    </div>
                    <div class="trip-card-actions">
                        <span style="font-family: var(--font-heading); font-weight: 700; font-size: 1.1rem; color: var(--primary);">
                            ${formatCurrency(act.estimated_cost, 'INR')}
                        </span>
                        <button class="btn btn-primary btn-sm" onclick="openScheduleCatalogActModal(${act.id})">
                            <i class="fa-solid fa-plus"></i> Schedule to Trip
                        </button>
                    </div>
                </div>
            </div>
        `;
    });

    html += `</div>`;
    main.innerHTML = html;
}

function filterActivityCat(cat) {
    state.selectedCategory = cat;
    renderActivitiesCatalog();
}

// ================= View 7: Admin Analytics =================
async function renderAdminDashboard() {
    const main = document.getElementById('main-content');
    main.innerHTML = `<div class="loading-state"><i class="fa-solid fa-spinner fa-spin"></i> Loading platform analytics...</div>`;

    const res = await apiRequest('/api/v1/admin/analytics');
    if (!res.success || !res.analytics) {
        main.innerHTML = `<div style="padding: 2rem; text-align: center;"><h3>Admin Access Denied</h3></div>`;
        return;
    }

    const a = res.analytics;

    let html = `
        <div class="section-header">
            <div>
                <h1 style="font-size: 2rem;">GlobeTrotter Admin &amp; Analytics</h1>
                <p style="color: var(--text-muted);">Real-time platform adoption, trip statistics, and destination demand.</p>
            </div>
        </div>

        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-icon-wrap indigo"><i class="fa-solid fa-users"></i></div>
                <div class="kpi-data">
                    <span class="kpi-label">Registered Travelers</span>
                    <span class="kpi-val">${a.total_users}</span>
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-icon-wrap emerald"><i class="fa-solid fa-map"></i></div>
                <div class="kpi-data">
                    <span class="kpi-label">Total Itineraries Created</span>
                    <span class="kpi-val">${a.total_trips}</span>
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-icon-wrap amber"><i class="fa-solid fa-money-bill-wave"></i></div>
                <div class="kpi-data">
                    <span class="kpi-label">Average Trip Budget</span>
                    <span class="kpi-val">${formatCurrency(a.avg_budget, 'INR')}</span>
                </div>
            </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
            <div style="background: #fff; border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 1.5rem;">
                <h3 style="margin-bottom: 1rem;"><i class="fa-solid fa-trophy" style="color: var(--accent);"></i> Top Visited Destinations</h3>
                <div style="display: flex; flex-direction: column; gap: 0.75rem;">
    `;

    (a.top_cities || []).forEach((c, idx) => {
        html += `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.6rem 0; border-bottom: 1px solid var(--border-subtle);">
                <span><strong>${idx + 1}. ${escapeHtml(c.name)}</strong>, ${escapeHtml(c.country)}</span>
                <span class="badge-chip primary">${c.visit_count} Itineraries</span>
            </div>
        `;
    });

    html += `
                </div>
            </div>

            <div style="background: #fff; border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 1.5rem;">
                <h3 style="margin-bottom: 1rem;"><i class="fa-solid fa-chart-pie" style="color: var(--primary);"></i> Travel Style Distribution</h3>
                <div style="display: flex; flex-direction: column; gap: 0.75rem;">
    `;

    (a.styles || []).forEach(s => {
        html += `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.6rem 0; border-bottom: 1px solid var(--border-subtle);">
                <span style="text-transform: capitalize;"><strong>${escapeHtml(s.travel_style)}</strong></span>
                <span class="badge-chip accent">${s.count} Trips</span>
            </div>
        `;
    });

    html += `
                </div>
            </div>
        </div>
    `;

    main.innerHTML = html;
}

// ================= Modals Management =================
function closeModal() {
    const container = document.getElementById('modal-container');
    if (container) container.innerHTML = '';
}

function openModal(contentHtml) {
    const container = document.getElementById('modal-container');
    if (!container) return;
    container.innerHTML = `
        <div class="modal-backdrop" onclick="if(event.target === this) closeModal()">
            <div class="modal-card">
                ${contentHtml}
            </div>
        </div>
    `;
}

// 1. Login Modal
function openLoginModal() {
    openModal(`
        <div class="modal-header">
            <h2 class="modal-title">Sign In to GlobeTrotter</h2>
            <button class="modal-close-btn" onclick="closeModal()">&times;</button>
        </div>
        <form onsubmit="event.preventDefault(); handleLogin(document.getElementById('login-email').value, document.getElementById('login-pass').value);">
            <div class="modal-body">
                <div class="form-group">
                    <label class="form-label">Email Address</label>
                    <input type="email" id="login-email" class="form-control" required placeholder="demo@globetrotter.travel">
                </div>
                <div class="form-group">
                    <label class="form-label">Password</label>
                    <input type="password" id="login-pass" class="form-control" required placeholder="••••••••">
                </div>
                <div style="background: var(--bg-subtle); padding: 0.85rem; border-radius: var(--radius-md); font-size: 0.85rem; margin-top: 1rem;">
                    <strong>Fast Hackathon Login:</strong>
                    <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem;">
                        <button type="button" class="btn btn-outline btn-sm" onclick="handleDemoLogin('traveler')">Demo Traveler</button>
                        <button type="button" class="btn btn-outline btn-sm" onclick="handleDemoLogin('admin')">Admin Demo</button>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline" onclick="openSignupModal()">Create Account</button>
                <button type="submit" class="btn btn-primary">Sign In</button>
            </div>
        </form>
    `);
}

// 2. Signup Modal
function openSignupModal() {
    openModal(`
        <div class="modal-header">
            <h2 class="modal-title">Create GlobeTrotter Account</h2>
            <button class="modal-close-btn" onclick="closeModal()">&times;</button>
        </div>
        <form onsubmit="event.preventDefault(); handleSignup(
            document.getElementById('signup-name').value,
            document.getElementById('signup-email').value,
            document.getElementById('signup-pass').value,
            document.getElementById('signup-curr').value,
            document.getElementById('signup-style').value
        );">
            <div class="modal-body">
                <div class="form-group">
                    <label class="form-label">Full Name</label>
                    <input type="text" id="signup-name" class="form-control" required placeholder="e.g. Rohan Sharma">
                </div>
                <div class="form-group">
                    <label class="form-label">Email Address</label>
                    <input type="email" id="signup-email" class="form-control" required placeholder="rohan@example.com">
                </div>
                <div class="form-group">
                    <label class="form-label">Password (min 6 chars)</label>
                    <input type="password" id="signup-pass" class="form-control" minlength="6" required placeholder="••••••••">
                </div>
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">Preferred Currency</label>
                        <select id="signup-curr" class="form-control">
                            <option value="INR">₹ INR (Indian Rupee)</option>
                            <option value="USD">$ USD (US Dollar)</option>
                            <option value="EUR">€ EUR (Euro)</option>
                            <option value="GBP">£ GBP (British Pound)</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Travel Style</label>
                        <select id="signup-style" class="form-control">
                            <option value="balanced">Balanced</option>
                            <option value="budget">Budget</option>
                            <option value="luxury">Luxury</option>
                            <option value="adventure">Adventure</option>
                            <option value="relaxed">Relaxed</option>
                        </select>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline" onclick="openLoginModal()">Already have an account?</button>
                <button type="submit" class="btn btn-primary">Create Account</button>
            </div>
        </form>
    `);
}

// 3. Create Trip Modal
function openCreateTripModal() {
    if (!state.user) {
        openLoginModal();
        return;
    }

    // Default dates: tomorrow and +6 days
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const end = new Date();
    end.setDate(end.getDate() + 7);

    const startStr = tomorrow.toISOString().split('T')[0];
    const endStr = end.toISOString().split('T')[0];

    openModal(`
        <div class="modal-header">
            <h2 class="modal-title"><i class="fa-solid fa-compass" style="color: var(--primary);"></i> Plan a New Itinerary</h2>
            <button class="modal-close-btn" onclick="closeModal()">&times;</button>
        </div>
        <form onsubmit="event.preventDefault(); handleCreateTripSubmit();">
            <div class="modal-body">
                <div class="form-group">
                    <label class="form-label">Itinerary Title *</label>
                    <input type="text" id="trip-name" class="form-control" required placeholder="e.g. Rajasthan Explorer" value="Rajasthan Explorer">
                </div>
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">Start Date *</label>
                        <input type="date" id="trip-start" class="form-control" required value="${startStr}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">End Date *</label>
                        <input type="date" id="trip-end" class="form-control" required value="${endStr}">
                    </div>
                </div>
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">Total Target Budget (INR/Currency) *</label>
                        <input type="number" id="trip-budget" class="form-control" required min="0" value="35000" placeholder="35000">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Number of Travelers *</label>
                        <input type="number" id="trip-travelers" class="form-control" required min="1" value="2">
                    </div>
                </div>
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">Currency</label>
                        <select id="trip-currency" class="form-control">
                            <option value="INR" selected>₹ INR (Indian Rupee)</option>
                            <option value="USD">$ USD (US Dollar)</option>
                            <option value="EUR">€ EUR (Euro)</option>
                            <option value="GBP">£ GBP (British Pound)</option>
                            <option value="AED">AED (UAE Dirham)</option>
                            <option value="SGD">S$ (Singapore Dollar)</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Travel Style</label>
                        <select id="trip-style" class="form-control">
                            <option value="balanced" selected>Balanced Explorer</option>
                            <option value="budget">Budget Backpacker</option>
                            <option value="luxury">Luxury &amp; Comfort</option>
                            <option value="adventure">Active Adventure</option>
                            <option value="relaxed">Relaxed &amp; Slow Travel</option>
                            <option value="family">Family Friendly</option>
                        </select>
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Cover Photo URL</label>
                    <input type="url" id="trip-cover" class="form-control" value="https://images.unsplash.com/photo-1603288967969-952467d027f6?auto=format&fit=crop&w=1200&q=80">
                </div>
                <div class="form-group">
                    <label class="form-label">Description / Travel Goals</label>
                    <textarea id="trip-desc" class="form-control" rows="2" placeholder="Highlights, personal expectations, notes...">Exploring historic forts, Rajasthani royal palaces, and authentic local cuisine across Delhi, Jaipur, and Udaipur.</textarea>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary btn-glow">Create &amp; Build Itinerary</button>
            </div>
        </form>
    `);
}

async function handleCreateTripSubmit() {
    const name = document.getElementById('trip-name').value.trim();
    const startDate = document.getElementById('trip-start').value;
    const endDate = document.getElementById('trip-end').value;
    const budget = parseFloat(document.getElementById('trip-budget').value) || 0;
    const travelers = parseInt(document.getElementById('trip-travelers').value) || 1;
    const currency = document.getElementById('trip-currency').value;
    const travelStyle = document.getElementById('trip-style').value;
    const cover = document.getElementById('trip-cover').value.trim();
    const desc = document.getElementById('trip-desc').value.trim();

    if (!name || !startDate || !endDate) {
        showToast('Please fill all required fields.', 'error');
        return;
    }
    if (endDate < startDate) {
        showToast('End date cannot be earlier than start date.', 'error');
        return;
    }

    const payload = {
        name,
        start_date: startDate,
        end_date: endDate,
        total_budget: budget,
        travelers_count: travelers,
        currency,
        travel_style: travelStyle,
        cover_image: cover,
        description: desc
    };

    const res = await apiRequest('/api/v1/trips', 'POST', payload);
    if (res.success && res.trip_id) {
        closeModal();
        showToast('Trip created! Loading Itinerary Builder...');
        navigateTo('itinerary', res.trip_id);
    } else {
        showToast(res.error || 'Failed to create trip', 'error');
    }
}

// 4. Add Destination Stop Modal
function openAddStopModal(tripId) {
    if (!state.destinations || state.destinations.length === 0) {
        apiRequest('/api/v1/destinations').then(r => {
            state.destinations = r.destinations || [];
            showAddStopModalContent(tripId);
        });
    } else {
        showAddStopModalContent(tripId);
    }
}

function showAddStopModalContent(tripId) {
    const trip = state.currentTrip;
    let optHtml = state.destinations.map(d => `<option value="${d.id}">${escapeHtml(d.name)}, ${escapeHtml(d.country)}</option>`).join('');

    openModal(`
        <div class="modal-header">
            <h2 class="modal-title"><i class="fa-solid fa-map-location-dot" style="color: var(--primary);"></i> Add Destination Stop</h2>
            <button class="modal-close-btn" onclick="closeModal()">&times;</button>
        </div>
        <form onsubmit="event.preventDefault(); handleAddStopSubmit(${tripId});">
            <div class="modal-body">
                <div class="form-group">
                    <label class="form-label">Select City Destination *</label>
                    <select id="stop-city" class="form-control" required>
                        ${optHtml}
                    </select>
                </div>
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">Arrival Date</label>
                        <input type="date" id="stop-arrival" class="form-control" value="${trip ? trip.start_date : ''}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Departure Date</label>
                        <input type="date" id="stop-departure" class="form-control" value="${trip ? trip.end_date : ''}">
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Stop Notes &amp; Accommodation Details</label>
                    <textarea id="stop-notes" class="form-control" rows="2" placeholder="e.g. Hotel Heritage Haveli, booking ref #9823..."></textarea>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Add Stop</button>
            </div>
        </form>
    `);
}

async function handleAddStopSubmit(tripId) {
    const cityId = document.getElementById('stop-city').value;
    const arrivalDate = document.getElementById('stop-arrival').value;
    const departureDate = document.getElementById('stop-departure').value;
    const notes = document.getElementById('stop-notes').value.trim();

    const res = await apiRequest(`/api/v1/trips/${tripId}/stops`, 'POST', {
        city_id: cityId,
        arrival_date: arrivalDate,
        departure_date: departureDate,
        notes
    });

    if (res.success) {
        closeModal();
        showToast('Destination stop added!');
        renderItineraryBuilder();
    } else {
        showToast(res.error || 'Failed to add stop', 'error');
    }
}

// 5. Add Activity Modal (with curated catalog browser)
async function openAddActivityModal(tripId, defaultDay = 1) {
    const trip = state.currentTrip;
    const stops = trip ? trip.stops || [] : [];
    
    // Fetch activities for the current trip's destination stops
    const res = await apiRequest('/api/v1/activities');
    const catalogActs = res.success ? (res.activities || []) : [];

    let stopOptions = stops.map(s => `<option value="${s.id}">${escapeHtml(s.city_name)}</option>`).join('');
    if (!stopOptions) stopOptions = `<option value="">(No specific stop assigned)</option>`;

    let actCards = catalogActs.map(a => `
        <div style="background: var(--bg-main); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 0.75rem; display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
            <div>
                <div style="font-weight: 700; font-size: 0.92rem;">${escapeHtml(a.name)}</div>
                <div style="font-size: 0.78rem; color: var(--text-muted);">
                    <span class="category-tag ${a.category}">${escapeHtml(a.category)}</span> &bull; ${escapeHtml(a.city_name)} &bull; ${formatCurrency(a.estimated_cost, trip ? trip.currency : 'INR')}
                </div>
            </div>
            <button type="button" class="btn btn-primary btn-sm" onclick="selectCatalogActivity(${a.id}, '${escapeHtml(a.name).replace(/'/g, "\\'")}', '${a.category}', ${a.duration_hours}, ${a.estimated_cost})">
                Select
            </button>
        </div>
    `).join('');

    openModal(`
        <div class="modal-header">
            <h2 class="modal-title"><i class="fa-solid fa-ticket" style="color: var(--primary);"></i> Schedule Activity to Day ${defaultDay}</h2>
            <button class="modal-close-btn" onclick="closeModal()">&times;</button>
        </div>
        <form onsubmit="event.preventDefault(); handleAddActivitySubmit(${tripId});">
            <div class="modal-body">
                <div style="margin-bottom: 1.25rem;">
                    <label class="form-label">Pick from Curated Experiences Catalog</label>
                    <div style="max-height: 180px; overflow-y: auto; border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 0.5rem;">
                        ${actCards}
                    </div>
                </div>

                <div style="border-top: 1px solid var(--border-color); padding-top: 1rem;">
                    <div class="form-group">
                        <label class="form-label">Activity Title *</label>
                        <input type="text" id="act-name" class="form-control" required placeholder="e.g. Amber Palace Sunset Tour">
                    </div>
                    <div class="form-row-2">
                        <div class="form-group">
                            <label class="form-label">Day Number (1, 2, ...)</label>
                            <input type="number" id="act-day" class="form-control" required min="1" max="${trip ? trip.duration_days : 30}" value="${defaultDay}">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Time Slot</label>
                            <input type="text" id="act-time" class="form-control" value="10:00" placeholder="09:30, 14:00...">
                        </div>
                    </div>
                    <div class="form-row-2">
                        <div class="form-group">
                            <label class="form-label">Category</label>
                            <select id="act-cat" class="form-control">
                                <option value="sightseeing">Sightseeing</option>
                                <option value="food">Food &amp; Dining</option>
                                <option value="culture">Culture &amp; History</option>
                                <option value="adventure">Adventure</option>
                                <option value="nature">Nature</option>
                                <option value="relaxation">Relaxation</option>
                                <option value="shopping">Shopping</option>
                                <option value="transport">Transit</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Estimated Cost (${trip ? trip.currency : 'INR'})</label>
                            <input type="number" id="act-cost" class="form-control" min="0" value="750">
                        </div>
                    </div>
                    <div class="form-row-2">
                        <div class="form-group">
                            <label class="form-label">Duration (Hours)</label>
                            <input type="number" step="0.5" id="act-dur" class="form-control" value="2.5">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Associated Stop</label>
                            <select id="act-stop" class="form-control">
                                ${stopOptions}
                            </select>
                        </div>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Schedule Activity</button>
            </div>
        </form>
    `);
}

function selectCatalogActivity(id, name, cat, dur, cost) {
    document.getElementById('act-name').value = name;
    document.getElementById('act-cat').value = cat;
    document.getElementById('act-dur').value = dur;
    document.getElementById('act-cost').value = cost;
}

async function handleAddActivitySubmit(tripId) {
    const name = document.getElementById('act-name').value.trim();
    const dayNumber = parseInt(document.getElementById('act-day').value) || 1;
    const scheduledTime = document.getElementById('act-time').value.trim();
    const category = document.getElementById('act-cat').value;
    const estimatedCost = parseFloat(document.getElementById('act-cost').value) || 0;
    const durationHours = parseFloat(document.getElementById('act-dur').value) || 2.0;
    const stopId = document.getElementById('act-stop').value || null;

    const res = await apiRequest(`/api/v1/trips/${tripId}/activities`, 'POST', {
        name,
        day_number: dayNumber,
        scheduled_time: scheduledTime,
        category,
        estimated_cost: estimatedCost,
        duration_hours: durationHours,
        stop_id: stopId
    });

    if (res.success) {
        closeModal();
        showToast('Activity added and budget recalculated!');
        renderItineraryBuilder();
    } else {
        showToast(res.error || 'Failed to schedule activity', 'error');
    }
}

// 6. Add Expense Modal
function openAddExpenseModal(tripId) {
    const trip = state.currentTrip;
    openModal(`
        <div class="modal-header">
            <h2 class="modal-title"><i class="fa-solid fa-receipt" style="color: var(--primary);"></i> Log Trip Expense / Logistic</h2>
            <button class="modal-close-btn" onclick="closeModal()">&times;</button>
        </div>
        <form onsubmit="event.preventDefault(); handleAddExpenseSubmit(${tripId});">
            <div class="modal-body">
                <div class="form-group">
                    <label class="form-label">Expense Description *</label>
                    <input type="text" id="exp-name" class="form-control" required placeholder="e.g. Flight Delhi to Jaipur, Heritage Hotel Stay...">
                </div>
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">Category *</label>
                        <select id="exp-cat" class="form-control" required>
                            <option value="accommodation">Accommodation / Hotel</option>
                            <option value="transportation">Transportation / Flights / Trains</option>
                            <option value="food">Food &amp; Dining</option>
                            <option value="activities">Activities &amp; Tours</option>
                            <option value="miscellaneous">Miscellaneous / Visa</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Amount (${trip ? trip.currency : 'INR'}) *</label>
                        <input type="number" id="exp-amount" class="form-control" required min="0" value="2500">
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Notes / Booking Confirmation Code</label>
                    <input type="text" id="exp-notes" class="form-control" placeholder="Booking Ref: PNR-98124">
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Save Expense</button>
            </div>
        </form>
    `);
}

async function handleAddExpenseSubmit(tripId) {
    const name = document.getElementById('exp-name').value.trim();
    const category = document.getElementById('exp-cat').value;
    const amount = parseFloat(document.getElementById('exp-amount').value) || 0;
    const notes = document.getElementById('exp-notes').value.trim();

    const res = await apiRequest(`/api/v1/trips/${tripId}/expenses`, 'POST', {
        name, category, amount, notes
    });

    if (res.success) {
        closeModal();
        showToast('Expense recorded & budget updated!');
        renderItineraryBuilder();
    } else {
        showToast(res.error || 'Failed to record expense', 'error');
    }
}

// 7. Share Itinerary Modal
async function openShareModal(tripId) {
    const res = await apiRequest(`/api/v1/trips/${tripId}/share`, 'POST', { is_public: true, share_budget: true });
    if (!res.success) {
        showToast(res.error || 'Failed to generate share link', 'error');
        return;
    }

    const fullShareUrl = `${window.location.origin}/shared/${res.share_token}`;

    openModal(`
        <div class="modal-header">
            <h2 class="modal-title"><i class="fa-solid fa-share-nodes" style="color: var(--primary);"></i> Share Itinerary Publicly</h2>
            <button class="modal-close-btn" onclick="closeModal()">&times;</button>
        </div>
        <div class="modal-body">
            <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 1.25rem;">
                Anyone with this secure link can view your itinerary and copy it directly to their own account.
            </p>
            <div class="form-group">
                <label class="form-label">Secure Public Link</label>
                <div style="display: flex; gap: 0.5rem;">
                    <input type="text" id="share-link-input" class="form-control" readonly value="${fullShareUrl}">
                    <button class="btn btn-primary" onclick="navigator.clipboard.writeText('${fullShareUrl}'); showToast('Share link copied to clipboard!');">
                        <i class="fa-regular fa-copy"></i> Copy
                    </button>
                </div>
            </div>
            <div style="background: var(--bg-subtle); padding: 1rem; border-radius: var(--radius-md); font-size: 0.88rem; display: flex; align-items: center; justify-content: space-between;">
                <span>Include budget breakdown in public view</span>
                <input type="checkbox" checked onchange="toggleShareBudget(${tripId}, this.checked)" style="width: 18px; height: 18px;">
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn btn-outline" onclick="window.open('${fullShareUrl}', '_blank')">
                <i class="fa-solid fa-arrow-up-right-from-square"></i> Open Public View
            </button>
            <button class="btn btn-primary" onclick="closeModal()">Done</button>
        </div>
    `);
}

async function toggleShareBudget(tripId, includeBudget) {
    await apiRequest(`/api/v1/trips/${tripId}/share`, 'POST', { is_public: true, share_budget: includeBudget });
    showToast(`Public budget view ${includeBudget ? 'enabled' : 'hidden'}.`);
}

// 8. Reorder Stops Handler
async function handleMoveStop(tripId, currentIndex, direction) {
    const trip = state.currentTrip;
    if (!trip || !trip.stops) return;

    const stops = [...trip.stops];
    const targetIndex = currentIndex + direction;
    if (targetIndex < 0 || targetIndex >= stops.length) return;

    // Swap
    const temp = stops[currentIndex];
    stops[currentIndex] = stops[targetIndex];
    stops[targetIndex] = temp;

    const stopIds = stops.map(s => s.id);
    const res = await apiRequest(`/api/v1/trips/${tripId}/stops/reorder`, 'POST', { stop_ids: stopIds });
    if (res.success) {
        showToast('Route reordered!');
        renderItineraryBuilder();
    }
}

// 9. Duplicate Trip Handler
async function handleDuplicateTrip(tripId) {
    const res = await apiRequest(`/api/v1/trips/${tripId}/duplicate`, 'POST');
    if (res.success && res.trip_id) {
        showToast('Itinerary duplicated into your account!');
        navigateTo('itinerary', res.trip_id);
    } else {
        showToast(res.error || 'Failed to duplicate trip', 'error');
    }
}

// 10. Copy Shared Trip Handler
async function handleCopySharedTrip(token) {
    if (!state.user) {
        showToast('Please sign in or use 1-click demo login to copy this trip.', 'info');
        openLoginModal();
        return;
    }

    const res = await apiRequest(`/api/v1/shared/${token}/copy`, 'POST');
    if (res.success && res.trip_id) {
        showToast('Itinerary cloned into your account!');
        navigateTo('itinerary', res.trip_id);
    } else {
        showToast(res.error || 'Failed to copy trip', 'error');
    }
}

// 11. Delete Trip Handler
async function handleDeleteTrip(tripId) {
    if (!confirm("Are you sure you want to delete this trip? All stops and scheduled activities will be permanently removed.")) {
        return;
    }
    const res = await apiRequest(`/api/v1/trips/${tripId}`, 'DELETE');
    if (res.success) {
        showToast('Trip deleted.');
        navigateTo('trips');
    } else {
        showToast(res.error || 'Failed to delete trip', 'error');
    }
}

// 12. Delete Stop & Activity Handlers
async function handleDeleteStop(tripId, stopId) {
    if (!confirm("Remove this destination stop and its activities from the trip?")) return;
    const res = await apiRequest(`/api/v1/trips/${tripId}/stops/${stopId}`, 'DELETE');
    if (res.success) {
        showToast('Stop removed.');
        renderItineraryBuilder();
    }
}

async function handleDeleteActivity(tripId, actId) {
    const res = await apiRequest(`/api/v1/trips/${tripId}/activities/${actId}`, 'DELETE');
    if (res.success) {
        showToast('Activity removed.');
        renderItineraryBuilder();
    }
}

async function handleDeleteExpense(tripId, expId) {
    const res = await apiRequest(`/api/v1/trips/${tripId}/expenses/${expId}`, 'DELETE');
    if (res.success) {
        showToast('Expense removed.');
        renderItineraryBuilder();
    }
}

// 13. Destination Detail Modal
async function openDestinationDetailModal(cityId) {
    const res = await apiRequest(`/api/v1/destinations/${cityId}`);
    if (!res.success || !res.destination) return;

    const dest = res.destination;
    const activities = dest.activities || [];

    let actsHtml = activities.map(a => `
        <div style="background: var(--bg-main); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 0.75rem 1rem; margin-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <div style="font-weight: 700;">${escapeHtml(a.name)}</div>
                <div style="font-size: 0.8rem; color: var(--text-muted);">
                    <span class="category-tag ${a.category}">${escapeHtml(a.category)}</span> &bull; ${a.duration_hours}h
                </div>
            </div>
            <span style="font-weight: 700; color: var(--primary);">${formatCurrency(a.estimated_cost, 'INR')}</span>
        </div>
    `).join('');

    openModal(`
        <div class="modal-header">
            <h2 class="modal-title">${escapeHtml(dest.name)}, ${escapeHtml(dest.country)}</h2>
            <button class="modal-close-btn" onclick="closeModal()">&times;</button>
        </div>
        <div class="modal-body">
            <img src="${dest.cover_image}" style="width: 100%; height: 200px; object-fit: cover; border-radius: var(--radius-md); margin-bottom: 1rem;">
            <p style="color: var(--text-main); line-height: 1.6; margin-bottom: 1rem;">${escapeHtml(dest.description)}</p>
            <div class="trip-meta-row" style="margin-bottom: 1.25rem;">
                <div class="trip-meta-item"><i class="fa-solid fa-clock"></i> Recommended: ${dest.recommended_duration_days} Days</div>
                <div class="trip-meta-item"><i class="fa-solid fa-coins"></i> Cost Index: ${'₹'.repeat(dest.cost_index || 2)}</div>
                <div class="trip-meta-item"><i class="fa-solid fa-fire"></i> Popularity: ${dest.popularity}/100</div>
            </div>
            <h4 style="margin-bottom: 0.75rem;">Top Curated Activities</h4>
            <div style="max-height: 200px; overflow-y: auto;">
                ${actsHtml}
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn btn-outline" onclick="closeModal()">Close</button>
            <button class="btn btn-primary" onclick="closeModal(); openAddToTripModal(${dest.id})">Add to Itinerary</button>
        </div>
    `);
}

// 14. Quick Add Destination to Existing Trip Modal
async function openAddToTripModal(cityId) {
    if (!state.user) {
        showToast('Please log in to add destinations to your trips.', 'info');
        openLoginModal();
        return;
    }

    const tRes = await apiRequest('/api/v1/trips');
    const trips = tRes.success ? (tRes.trips || []) : [];

    if (trips.length === 0) {
        showToast('Please create a trip first.', 'info');
        openCreateTripModal();
        return;
    }

    const optHtml = trips.map(t => `<option value="${t.id}">${escapeHtml(t.name)} (${formatDateRange(t.start_date, t.end_date)})</option>`).join('');

    openModal(`
        <div class="modal-header">
            <h2 class="modal-title">Add Destination to Trip</h2>
            <button class="modal-close-btn" onclick="closeModal()">&times;</button>
        </div>
        <form onsubmit="event.preventDefault(); handleAddCityToSelectedTrip(${cityId});">
            <div class="modal-body">
                <div class="form-group">
                    <label class="form-label">Select Target Trip</label>
                    <select id="target-trip-id" class="form-control">
                        ${optHtml}
                    </select>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Add Stop &amp; Open Builder</button>
            </div>
        </form>
    `);
}

async function handleAddCityToSelectedTrip(cityId) {
    const tripId = document.getElementById('target-trip-id').value;
    const res = await apiRequest(`/api/v1/trips/${tripId}/stops`, 'POST', { city_id: cityId });
    if (res.success) {
        closeModal();
        showToast('Destination added to itinerary!');
        navigateTo('itinerary', tripId);
    } else {
        showToast(res.error || 'Failed to add destination', 'error');
    }
}

// 15. User Profile Modal
function openProfileModal() {
    if (!state.user) return;
    openModal(`
        <div class="modal-header">
            <h2 class="modal-title"><i class="fa-solid fa-user-gear" style="color: var(--primary);"></i> Traveler Profile &amp; Preferences</h2>
            <button class="modal-close-btn" onclick="closeModal()">&times;</button>
        </div>
        <form onsubmit="event.preventDefault(); handleUpdateProfile();">
            <div class="modal-body">
                <div class="form-group">
                    <label class="form-label">Full Name</label>
                    <input type="text" id="prof-name" class="form-control" value="${escapeHtml(state.user.name)}">
                </div>
                <div class="form-group">
                    <label class="form-label">Email Address (Account ID)</label>
                    <input type="text" class="form-control" readonly value="${escapeHtml(state.user.email)}" disabled>
                </div>
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="form-label">Preferred Currency</label>
                        <select id="prof-curr" class="form-control">
                            <option value="INR" ${state.user.preferred_currency === 'INR' ? 'selected' : ''}>₹ INR</option>
                            <option value="USD" ${state.user.preferred_currency === 'USD' ? 'selected' : ''}>$ USD</option>
                            <option value="EUR" ${state.user.preferred_currency === 'EUR' ? 'selected' : ''}>€ EUR</option>
                            <option value="GBP" ${state.user.preferred_currency === 'GBP' ? 'selected' : ''}>£ GBP</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Travel Style</label>
                        <select id="prof-style" class="form-control">
                            <option value="balanced" ${state.user.preferred_travel_style === 'balanced' ? 'selected' : ''}>Balanced</option>
                            <option value="budget" ${state.user.preferred_travel_style === 'budget' ? 'selected' : ''}>Budget</option>
                            <option value="luxury" ${state.user.preferred_travel_style === 'luxury' ? 'selected' : ''}>Luxury</option>
                            <option value="adventure" ${state.user.preferred_travel_style === 'adventure' ? 'selected' : ''}>Adventure</option>
                            <option value="relaxed" ${state.user.preferred_travel_style === 'relaxed' ? 'selected' : ''}>Relaxed</option>
                        </select>
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Bio / Travel Manifesto</label>
                    <textarea id="prof-bio" class="form-control" rows="2">${escapeHtml(state.user.bio || '')}</textarea>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline" onclick="closeModal()">Close</button>
                <button type="submit" class="btn btn-primary">Save Changes</button>
            </div>
        </form>
    `);
}

async function handleUpdateProfile() {
    const name = document.getElementById('prof-name').value.trim();
    const curr = document.getElementById('prof-curr').value;
    const style = document.getElementById('prof-style').value;
    const bio = document.getElementById('prof-bio').value.trim();

    const res = await apiRequest('/api/v1/auth/profile', 'PUT', {
        name, preferred_currency: curr, preferred_travel_style: style, bio
    });

    if (res.success && res.user) {
        state.user = res.user;
        closeModal();
        renderAuthNav();
        showToast('Profile preferences updated!');
    } else {
        showToast(res.error || 'Failed to update profile', 'error');
    }
}

// ================= App Initialization =================
window.addEventListener('DOMContentLoaded', async () => {
    // Check if initial URL is a public shared route
    const path = window.location.pathname;
    if (path.startsWith('/shared/')) {
        const token = path.split('/shared/')[1];
        state.sharedToken = token;
        await initAuth();
        navigateTo('shared', token);
        return;
    }

    await initAuth();
    navigateTo('dashboard');
});
