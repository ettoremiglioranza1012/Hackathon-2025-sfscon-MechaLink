import streamlit as st
from pages import (
    analytics,
    settings,
    robotCleaningMonitoring,
    robotDeliveringMonitoring,
    robotLiftingMonitoring,
)
from pages import delivery, industrial
from utils.helpers import get_shops_from_api
import os

# Configure page settings
st.set_page_config(
    page_title="Telmekom Prototype Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS and JavaScript to make sidebar non-collapsible and improve styling
st.markdown(
    """
    <style>
        /* Hide ALL possible sidebar collapse buttons - comprehensive selectors */
        button[title="Close sidebar"],
        button[title="Close sidebar"][aria-label="Close sidebar"],
        button[kind="header"][aria-label="Close sidebar"],
        button[aria-label="Close sidebar"],
        button[aria-label*="Close sidebar"],
        button[aria-label*="close sidebar"],
        [data-testid="collapsedControl"],
        [data-testid="stSidebar"] button[aria-label*="Close"],
        [data-testid="stSidebar"] button[title*="Close"],
        header button[aria-label*="Close sidebar"],
        header button[title*="Close sidebar"] {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
            width: 0 !important;
            height: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
        }

        /* Ensure sidebar is always visible and has proper width - prevent collapse */
        section[data-testid="stSidebar"] {
            min-width: 280px !important;
            width: 280px !important;
            max-width: 280px !important;
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
        }

        /* Prevent sidebar from collapsing - force width on all child elements */
        section[data-testid="stSidebar"] > div {
            width: 280px !important;
            min-width: 280px !important;
            max-width: 280px !important;
        }

        /* Prevent the main content from expanding when sidebar would collapse */
        .main .block-container {
            max-width: calc(100% - 280px) !important;
        }

        /* Hide any overlay or backdrop that might allow collapsing */
        .stApp > div:first-child {
            display: flex !important;
        }

        /* Hide default Streamlit navigation (search field and page links) - AGGRESSIVE */
        [data-testid="stSidebarNav"],
        [data-testid="stSidebarNav"] *,
        div[data-testid="stSidebarNav"],
        nav[data-testid="stSidebarNav"],
        section[data-testid="stSidebar"] > div > div:first-child:not(:has([data-testid="stSelectbox"])):has(nav),
        section[data-testid="stSidebar"] > div > div:first-child:not(:has([data-testid="stSelectbox"])):has(ul),
        section[data-testid="stSidebar"] > div > div:first-child:not(:has([data-testid="stSelectbox"])):has(a),
        section[data-testid="stSidebar"] nav:not(.custom-nav),
        section[data-testid="stSidebar"] nav *,
        section[data-testid="stSidebar"] ul:not([data-testid="stSelectbox"] ul),
        section[data-testid="stSidebar"] li:not([data-testid="stSelectbox"] li),
        section[data-testid="stSidebar"] a:not(button a):not([data-testid="stSelectbox"] a),
        section[data-testid="stSidebar"] input[type="text"]:not([data-testid="stSelectbox"] input),
        section[data-testid="stSidebar"] input[type="search"],
        /* Target the container that holds the page links */
        section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"],
        section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"],
        /* Hide by class names that Streamlit uses */
        section[data-testid="stSidebar"] .css-1544g2n,
        section[data-testid="stSidebar"] .css-17lntkn,
        section[data-testid="stSidebar"] [class*="viewerBadge"],
        section[data-testid="stSidebar"] [class*="stSidebarNav"],
        /* Target specific Streamlit page navigation */
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:first-child:has(nav),
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:first-child:has(ul),
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:first-child:has(a[href]) {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            height: 0 !important;
            width: 0 !important;
            max-height: 0 !important;
            max-width: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
            overflow: hidden !important;
            position: absolute !important;
            left: -9999px !important;
        }

        /* Style section headers */
        .sidebar-section-header {
            font-size: 0.75rem;
            font-weight: 600;
            color: #808495;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-top: 1.5rem;
            margin-bottom: 0.5rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #e0e0e0;
        }

        /* Style navigation buttons to look better */
        div[data-testid="stSidebar"] button[kind="primary"] {
            background-color: #e0e0e0;
            font-weight: 600;
            color: #1f1f1f;
            border: 1px solid #c0c0c0;
        }

        div[data-testid="stSidebar"] button[kind="secondary"] {
            background-color: transparent;
            font-weight: normal;
            border: 1px solid transparent;
        }

        div[data-testid="stSidebar"] button:hover {
            background-color: #f0f2f6;
            border-color: #d0d0d0;
        }

        /* Improve selectbox styling */
        div[data-testid="stSidebar"] .stSelectbox > div > div {
            background-color: white;
        }

        /* Add spacing to shop selection section */
        div[data-testid="stSidebar"] h3 {
            margin-top: 1rem;
            margin-bottom: 0.5rem;
        }
    </style>

    <script>
        // Aggressively prevent sidebar collapse and remove default navigation
        function preventSidebarCollapse() {
            // Hide all collapse buttons
            const collapseButtons = document.querySelectorAll(
                'button[aria-label*="Close sidebar"], ' +
                'button[title*="Close sidebar"], ' +
                '[data-testid="collapsedControl"], ' +
                'button[aria-label*="close sidebar"]'
            );
            collapseButtons.forEach(btn => {
                btn.style.display = 'none';
                btn.style.visibility = 'hidden';
                btn.style.opacity = '0';
                btn.style.pointerEvents = 'none';
                btn.style.width = '0';
                btn.style.height = '0';
                btn.remove();
            });

            // Remove default Streamlit navigation (search field and page links) - AGGRESSIVE
            const sidebar = document.querySelector('section[data-testid="stSidebar"]');
            if (sidebar) {
                // Remove ALL navigation elements - be very aggressive
                const navSelectors = [
                    '[data-testid="stSidebarNav"]',
                    'nav[data-testid="stSidebarNav"]',
                    'nav',
                    'ul',
                    'li',
                    'a',
                    'input[type="text"]',
                    'input[type="search"]',
                    '[data-testid="stSidebarNavItems"]',
                    '[data-testid="stSidebarNavLink"]',
                    '[class*="viewerBadge"]',
                    '[class*="stSidebarNav"]',
                ];

                navSelectors.forEach(selector => {
                    const elements = sidebar.querySelectorAll(selector);
                    elements.forEach(el => {
                        // Only remove if it's not inside our custom content
                        // Check if it's part of the selectbox
                        const isSelectbox = el.closest('[data-testid="stSelectbox"]') || 
                                          el.closest('.stSelectbox') ||
                                          el.tagName === 'SELECT' ||
                                          el.type === 'select-one';

                        if (!isSelectbox) {
                            el.style.display = 'none';
                            el.style.visibility = 'hidden';
                            el.style.height = '0';
                            el.style.position = 'absolute';
                            el.style.left = '-9999px';
                            el.remove();
                        }
                    });
                });

                // Remove the first child div if it contains navigation
                const sidebarChildren = sidebar.children;
                if (sidebarChildren.length > 0) {
                    const firstChild = sidebarChildren[0];
                    // Check if it contains navigation elements
                    const hasNav = firstChild.querySelector('nav, ul, li') || 
                                 firstChild.querySelector('a[href]') ||
                                 firstChild.querySelector('input[type="text"]');
                    if (hasNav) {
                        firstChild.style.display = 'none';
                        firstChild.style.height = '0';
                        firstChild.style.overflow = 'hidden';
                        firstChild.remove();
                    }
                }

                // Ensure sidebar is always visible
                sidebar.style.minWidth = '280px';
                sidebar.style.width = '280px';
                sidebar.style.maxWidth = '280px';
                sidebar.style.display = 'block';
                sidebar.style.visibility = 'visible';
                sidebar.style.opacity = '1';

                // Prevent any click events that might collapse it
                sidebar.addEventListener('click', function(e) {
                    // Allow clicks inside sidebar, but prevent collapse triggers
                    const target = e.target;
                    if (target && (
                        target.getAttribute('aria-label')?.includes('Close sidebar') ||
                        target.getAttribute('title')?.includes('Close sidebar')
                    )) {
                        e.preventDefault();
                        e.stopPropagation();
                        e.stopImmediatePropagation();
                        return false;
                    }
                }, true);
            }

            // Monitor for any attempts to hide the sidebar
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'attributes' || mutation.type === 'childList') {
                        const sidebar = document.querySelector('section[data-testid="stSidebar"]');
                        if (sidebar) {
                            const style = window.getComputedStyle(sidebar);
                            if (style.display === 'none' || style.visibility === 'hidden' || style.width === '0px') {
                                sidebar.style.display = 'block';
                                sidebar.style.visibility = 'visible';
                                sidebar.style.width = '280px';
                            }
                        }

                        // Remove any new collapse buttons that appear
                        const newButtons = document.querySelectorAll(
                            'button[aria-label*="Close sidebar"], ' +
                            'button[title*="Close sidebar"]'
                        );
                        newButtons.forEach(btn => {
                            if (btn.offsetParent !== null) {
                                btn.remove();
                            }
                        });

                        // Remove any new default navigation elements that appear - AGGRESSIVE
                        const sidebar = document.querySelector('section[data-testid="stSidebar"]');
                        if (sidebar) {
                            // Remove all navigation-related elements
                            const navSelectors = [
                                '[data-testid="stSidebarNav"]',
                                'nav',
                                'ul',
                                'li', 
                                'a[href]',
                                'input[type="text"]',
                                'input[type="search"]',
                            ];

                            navSelectors.forEach(selector => {
                                const elements = sidebar.querySelectorAll(selector);
                                elements.forEach(el => {
                                    // Check if it's part of the selectbox or our custom buttons
                                    const isSelectbox = el.closest('[data-testid="stSelectbox"]') ||
                                                      el.closest('.stSelectbox') ||
                                                      el.tagName === 'SELECT';
                                    const isButton = el.tagName === 'BUTTON' || el.closest('button');

                                    if (!isSelectbox && !isButton) {
                                        el.style.display = 'none';
                                        el.style.position = 'absolute';
                                        el.style.left = '-9999px';
                                        el.remove();
                                    }
                                });
                            });
                        }
                    }
                });
            });

            // Observe the entire document for changes
            observer.observe(document.body, {
                childList: true,
                subtree: true,
                attributes: true,
                attributeFilter: ['style', 'class', 'aria-label', 'title']
            });
        }

        // Run immediately
        preventSidebarCollapse();

        // Run on DOMContentLoaded
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', preventSidebarCollapse);
        }

        // Run on every page navigation/rerun
        window.addEventListener('load', preventSidebarCollapse);

        // Run periodically to catch any dynamic changes
        setInterval(preventSidebarCollapse, 500);

        // Override any Streamlit functions that might collapse the sidebar
        if (window.parent && window.parent.streamlit) {
            const originalRerun = window.parent.streamlit.rerun;
            if (originalRerun) {
                window.parent.streamlit.rerun = function() {
                    setTimeout(preventSidebarCollapse, 100);
                    return originalRerun.apply(this, arguments);
                };
            }
        }
    </script>
""",
    unsafe_allow_html=True,
)

# Initialize session state for page navigation
if "current_page" not in st.session_state:
    st.session_state.current_page = "🏠 Home"

# Shop Selection Section - AT THE TOP
st.sidebar.markdown("### 🏪 Shop Selection")


# Get shops from API (cached to avoid repeated calls)
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_shops():
    """Fetch shops from API. Returns empty list on error."""
    try:
        return get_shops_from_api()
    except Exception:
        # Return empty list on error - error handling is done in the UI
        return []


try:
    shops_data = fetch_shops()

    if shops_data and len(shops_data) > 0:
        # Create options for selectbox
        # Handle different data formats from API
        shop_options = []
        shop_id_map = {}

        for shop in shops_data:
            shop_id = shop.get("shop_id") or shop.get("id")
            shop_name = shop.get("shop_name") or shop.get("name") or f"Shop {shop_id}"

            if shop_id:
                display_name = f"{shop_name} ({shop_id})"
                shop_options.append(display_name)
                shop_id_map[display_name] = shop_id

        # Initialize selected shop_id in session state
        if (
            "selected_shop_id" not in st.session_state
            or st.session_state.selected_shop_id is None
        ):
            if shop_options:
                st.session_state.selected_shop_id = shop_id_map[shop_options[0]]
            else:
                st.session_state.selected_shop_id = None

        # Create selectbox
        if shop_options:
            # Find the index of the currently selected shop
            current_shop_display = None
            for display_name, shop_id in shop_id_map.items():
                if shop_id == st.session_state.selected_shop_id:
                    current_shop_display = display_name
                    break

            if current_shop_display and current_shop_display in shop_options:
                current_index = shop_options.index(current_shop_display)
            else:
                current_index = 0
                st.session_state.selected_shop_id = shop_id_map[shop_options[0]]

            selected_shop = st.sidebar.selectbox(
                "Select Shop",
                options=shop_options,
                index=current_index,
                key="shop_selectbox",
                label_visibility="visible",
            )

            # Update session state with selected shop_id
            st.session_state.selected_shop_id = shop_id_map[selected_shop]

            # Display selected shop info
            st.sidebar.caption(f"Selected: {st.session_state.selected_shop_id}")
        else:
            st.sidebar.warning("No shops available")
            st.session_state.selected_shop_id = None
    else:
        st.sidebar.warning("⚠️ No shops available. Please check your API connection.")
        st.session_state.selected_shop_id = None

except Exception as e:
    st.sidebar.error(f"❌ Error loading shops: {str(e)}")
    st.session_state.selected_shop_id = None

# Add separator after shop selection
st.sidebar.markdown("---")

# Sidebar Navigation
st.sidebar.markdown("## 📚 Navigation")

# Define page sections with organized structure
PAGE_SECTIONS = {
    "Main": {
        "🏠 Home": None,  # Home page is rendered directly in app.py
        "📈 Analytics": analytics,
        "🤖 Cleaning Monitoring": robotCleaningMonitoring,
        "🤖 Delivery Monitoring": robotDeliveringMonitoring,
        "🤖 Inventory Monitoring": robotLiftingMonitoring,
    },
    "Task": {
        "🚚 Delivery": delivery,
        "🏭 Industrial": industrial,
    },
    "Configuration": {
        "⚙️ Settings": settings,
    },
}

# Render page sections with headers
for section_name, pages in PAGE_SECTIONS.items():
    st.sidebar.markdown(
        f'<div class="sidebar-section-header">{section_name}</div>',
        unsafe_allow_html=True,
    )

    for page_name, page_module in pages.items():
        # Determine if this is the active page
        is_active = st.session_state.current_page == page_name

        # Create a button for each page
        if st.sidebar.button(
            page_name,
            key=f"nav_{page_name}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state.current_page = page_name
            st.rerun()

# Render selected page
current_page_name = st.session_state.current_page
page_found = False

# Check if Home page is selected
if current_page_name == "🏠 Home":
    # Render Home page content directly
    st.title("🤖 Telmekom Robot Management Dashboard")

    # Hero section with captivating introduction
    st.markdown("""
        ### Welcome to Your Command Center for Intelligent Robot Operations

        Harness the power of real-time data analytics to optimize your robotic fleet. 
        This dashboard provides comprehensive insights into robot performance, task execution, 
        and operational efficiency—all in one place.
    """)

    st.markdown("---")

    # Main features section
    st.header("🎯 Key Features")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
            ### 📊 Control Robot Performance

            Monitor and analyze your robot fleet's performance metrics in real-time:

            - **Performance Analytics** - Track efficiency, uptime, and productivity metrics
            - **Resource Optimization** - Monitor power consumption, water usage, and operational costs
            - **Comparative Analysis** - Compare performance across different robot models and shops
            - **Historical Trends** - Identify patterns and optimize operations over time

            Make data-driven decisions to maximize your robotic fleet's efficiency.
        """)

    with col2:
        st.markdown("""
            ### 🔍 Task Visibility at a Glance

            Get instant visibility into all robot operations across your network:

            - **Real-Time Task Monitoring** - See what each robot is doing right now
            - **Task Completion Tracking** - Monitor cleaning, delivery, and industrial tasks
            - **Operational Status** - Quickly identify active, idle, or maintenance-required robots
            - **Multi-Shop Overview** - Manage operations across all your locations from one dashboard

            Stay informed and respond quickly to operational needs.
        """)

    st.markdown("---")

    # Quick start guide
    st.header("🚀 Getting Started")

    st.markdown("""
        1. **Select Your Shop** - Use the dropdown in the sidebar to choose which location to analyze
        2. **Explore Analytics** - Navigate to the Analytics page for detailed performance metrics
        3. **Monitor Tasks** - Check the Tasks page to see real-time robot operations
        4. **Customize Settings** - Adjust your preferences in the Settings page
    """)

    # Call to action
    st.info(
        "👈 **Start by selecting a shop from the sidebar, then navigate to Analytics or Tasks to dive into the data!**"
    )
    page_found = True
else:
    # Render other pages
    for section_pages in PAGE_SECTIONS.values():
        if current_page_name in section_pages:
            page_module = section_pages[current_page_name]
            page_module.render()
            page_found = True
            break

if not page_found:
    # Default to Home if page not found
    st.session_state.current_page = "🏠 Home"
    st.rerun()
