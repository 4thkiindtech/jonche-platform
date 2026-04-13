/* ── Product Image Generation JS ──────────────────────────────────────────── */

/**
 * Image Generation Utilities
 * Handles generation of 360° views and size comparison graphics
 */

const ImageGenerator = {
  /**
   * Generate 360° angle views for a product
   * @param {number} productId - Product ID
   * @param {Object} options - Generation options
   * @returns {Promise<Object>} Generation result
   */
  async generateAngles(productId, options = {}) {
    const angles = options.angles || [0, 90, 180, 270];
    const baseImageUrl = options.baseImageUrl || null;

    const response = await fetch(`/api/admin/products/${productId}/generate-angles`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        angles,
        base_image_url: baseImageUrl,
      }),
      credentials: 'include',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to generate angles');
    }

    return await response.json();
  },

  /**
   * Generate size comparison graphic
   * @param {number} productId - Product ID
   * @param {Object} options - Generation options
   * @returns {Promise<Object>} Generation result
   */
  async generateSizeComparison(productId, options = {}) {
    const referenceType = options.referenceType || 'credit_card';
    const baseImageUrl = options.baseImageUrl || null;

    const response = await fetch(
      `/api/admin/products/${productId}/generate-size-comparison`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reference_type: referenceType,
          base_image_url: baseImageUrl,
        }),
        credentials: 'include',
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to generate size comparison');
    }

    return await response.json();
  },

  /**
   * Generate complete multiview (angles + size comparison)
   * @param {number} productId - Product ID
   * @param {Object} options - Generation options
   * @returns {Promise<Object>} Generation result
   */
  async generateMultiview(productId, options = {}) {
    const baseImageUrl = options.baseImageUrl || null;

    const response = await fetch(
      `/api/admin/products/${productId}/generate-multiview`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          base_image_url: baseImageUrl,
        }),
        credentials: 'include',
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to generate multiview');
    }

    return await response.json();
  },

  /**
   * Show loading toast
   * @param {string} message - Message to display
   * @returns {Object} Toast element
   */
  showToast(message, type = 'info') {
    const toastId = `toast-${Date.now()}`;
    const toastHTML = `
      <div id="${toastId}" class="toast" role="alert">
        <div class="toast-header bg-${type} text-white">
          <strong class="me-auto">
            <i class="fas fa-${
              type === 'success' ? 'check-circle' : 
              type === 'error' ? 'exclamation-circle' : 
              'info-circle'
            }"></i>
          </strong>
          <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
        </div>
        <div class="toast-body">${message}</div>
      </div>
    `;

    const container = document.querySelector('.toast-container') || 
                     (() => {
                       const c = document.createElement('div');
                       c.className = 'toast-container position-fixed bottom-0 end-0 p-3';
                       document.body.appendChild(c);
                       return c;
                     })();

    const toastEl = document.createElement('div');
    toastEl.innerHTML = toastHTML;
    container.appendChild(toastEl.firstElementChild);

    const toast = new bootstrap.Toast(document.getElementById(toastId));
    toast.show();

    setTimeout(() => {
      document.getElementById(toastId)?.remove();
    }, 5000);

    return toast;
  },
};

/**
 * Admin Image Generation Form Handler
 * Integrates with admin product management interface
 */
document.addEventListener('DOMContentLoaded', () => {
  // Handle generate angles button
  const generateAnglesBtn = document.getElementById('generateAnglesBtn');
  if (generateAnglesBtn) {
    generateAnglesBtn.addEventListener('click', async () => {
      const productId = parseInt(generateAnglesBtn.dataset.productId);
      const originalText = generateAnglesBtn.innerHTML;

      try {
        generateAnglesBtn.disabled = true;
        generateAnglesBtn.innerHTML = 
          '<span class="spinner-border spinner-border-sm me-2"></span>Generating...';

        const result = await ImageGenerator.generateAngles(productId);
        
        ImageGenerator.showToast(
          `Generated ${result.angle_count} angle views!`,
          'success'
        );

        // Refresh product view if available
        if (window.refreshProductView) {
          window.refreshProductView();
        }
      } catch (error) {
        console.error('Generation failed:', error);
        ImageGenerator.showToast(error.message, 'error');
      } finally {
        generateAnglesBtn.disabled = false;
        generateAnglesBtn.innerHTML = originalText;
      }
    });
  }

  // Handle generate size comparison button
  const generateSizeBtn = document.getElementById('generateSizeComparisonBtn');
  if (generateSizeBtn) {
    generateSizeBtn.addEventListener('click', async () => {
      const productId = parseInt(generateSizeBtn.dataset.productId);
      const originalText = generateSizeBtn.innerHTML;

      try {
        generateSizeBtn.disabled = true;
        generateSizeBtn.innerHTML = 
          '<span class="spinner-border spinner-border-sm me-2"></span>Generating...';

        const result = await ImageGenerator.generateSizeComparison(productId);
        
        ImageGenerator.showToast(
          `Generated size comparison!`,
          'success'
        );

        // Refresh product view if available
        if (window.refreshProductView) {
          window.refreshProductView();
        }
      } catch (error) {
        console.error('Generation failed:', error);
        ImageGenerator.showToast(error.message, 'error');
      } finally {
        generateSizeBtn.disabled = false;
        generateSizeBtn.innerHTML = originalText;
      }
    });
  }

  // Handle generate all button
  const generateAllBtn = document.getElementById('generateAllBtn');
  if (generateAllBtn) {
    generateAllBtn.addEventListener('click', async () => {
      const productId = parseInt(generateAllBtn.dataset.productId);
      const originalText = generateAllBtn.innerHTML;

      try {
        generateAllBtn.disabled = true;
        generateAllBtn.innerHTML = 
          '<span class="spinner-border spinner-border-sm me-2"></span>Generating all...';

        const result = await ImageGenerator.generateMultiview(productId);
        
        ImageGenerator.showToast(
          `Generated ${result.images_count} enhanced views!`,
          'success'
        );

        // Refresh product view if available
        if (window.refreshProductView) {
          window.refreshProductView();
        }
      } catch (error) {
        console.error('Generation failed:', error);
        ImageGenerator.showToast(error.message, 'error');
      } finally {
        generateAllBtn.disabled = false;
        generateAllBtn.innerHTML = originalText;
      }
    });
  }
});
