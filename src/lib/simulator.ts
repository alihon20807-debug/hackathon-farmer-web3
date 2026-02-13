/**
 * Agri-Oracle Logic Abstraction Layer
 * 
 * TODO: Replace these mock functions with real API calls to your backend.
 */

// Central India (Maharashtra/Madhya Pradesh region) - approximate center
const LAT_BASE = 20.5937;
const LNG_BASE = 78.9629;

/**
 * Generates a mock "predicted price" for onions based on diesel tax.
 * The logic assumes higher fuel costs drive up transport costs, increasing the final price.
 * 
 * @param dieselTax - The current simulated diesel tax in ₹/Litre
 * @param dayIndex - The day index (0-29) for the 30-day forecast
 * @returns Predicted price in ₹/kg
 */
export function calculateOnionPrice(dieselTax: number, dayIndex: number): number {
    // precise logic: higher tax = higher base price
    // seasonality: simulated by sine wave
    const basePrice = 40 + (dieselTax * 0.5);
    const seasonality = Math.sin(dayIndex / 5) * 10;
    const noise = Math.random() * 5;

    return Math.round((basePrice + seasonality + noise) * 100) / 100;
}

/**
 * Returns a random coordinate near the agricultural belt in Central India.
 * Used for the "Satellite NDVI Vision" feed.
 */
export function getSatelliteCoordinates() {
    // Random offset within ~100km
    const latOffset = (Math.random() - 0.5) * 2;
    const lngOffset = (Math.random() - 0.5) * 2;

    return {
        lat: (LAT_BASE + latOffset).toFixed(4),
        lng: (LNG_BASE + lngOffset).toFixed(4)
    };
}

/**
 * Mock Status for the Satellite Feed
 */
export function getSatelliteStatus(): "ACQUIRING" | "ANALYZING" | "TRANSMITTING" {
    const statuses = ["ACQUIRING", "ANALYZING", "TRANSMITTING"] as const;
    return statuses[Math.floor(Math.random() * statuses.length)];
}
