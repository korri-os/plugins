// The build composition supplies the publisher namespace before Nix signing.
// Login is an explicit operator `tailscale up`, not a daemon credential effect.
export const name = "tailscale"
export const title = "Tailscale"
export const services = ["tailscaled"]
