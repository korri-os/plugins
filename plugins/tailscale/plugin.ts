// The build composition supplies the publisher namespace before Nix signing.
export const name = "tailscale"
export const title = "Tailscale"
export const services = ["tailscaled"]

// Core ADR 0089: korrid shows this sign-in, and offers it as a setup step.
// The account host drives the plugin's own tailscale CLI; the logo is
// Tailscale's mark (README.md, "Logo").
export const accounts = {
  tailscale: {
    title: "Tailscale",
    program: "korri-tailscale-account",
    logo: "logo",
    offer: "Private network: reach your devices from anywhere",
  },
}
