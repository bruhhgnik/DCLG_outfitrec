/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      // Allow all HTTPS images (needed for various CDNs)
      {
        protocol: 'https',
        hostname: '**',
      },
      // Allow HTTP images as fallback
      {
        protocol: 'http',
        hostname: '**',
      },
    ],
  },
};

export default nextConfig;
