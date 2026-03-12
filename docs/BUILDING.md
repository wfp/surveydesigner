# Building Survey Designer

## Frontend Build Process

The frontend application requires **Node.js 20.x** and **pnpm** (version 10.8.0) to build the production artifact.

### Prerequisites

1. Install Node.js v20.x.
2. Enable `corepack` and set up `pnpm`:
   ```bash
   corepack enable
   corepack prepare pnpm@10.8.0 --activate
   ```

### Build Instructions

1. **Install Dependencies:**
   Navigate into the frontend project directory and install the required dependencies using pnpm.

   ```bash
   pnpm install
   ```

2. **Configure Environment Variables:**
   Before building, you need to configure the following environment variables according to your target environment (e.g., development or production):
   - `VITE_APP_API_ENDPOINT`: The URL of your backend API.
   - `VITE_CLARITY_PROJECT_ID`: (Optional) Your Microsoft Clarity project ID if you are using analytics.
   - `VITE_BUILD_ID`: (Optional) An identifier for the build, such as a build number.

   Example:

   ```bash
   export VITE_APP_API_ENDPOINT="https://api.example.com"
   export VITE_CLARITY_PROJECT_ID="your-clarity-project-id"
   ```

3. **Build the Artifact:**
   Run the build script, ensuring your environment variables are available:

   ```bash
   pnpm build
   ```

4. **Output Directory:**
   Once the build completes successfully, the compiled, production-ready artifact will be located in the `dist/` directory. You can copy the contents of this folder to your serving or staging environment.

---

## Backend Build Process

The backend application is containerized using **Docker**. Ensure you have Docker installed and use **BuildKit** for improved performance.

### Build Instructions

1. **Prepare Environment File:**
   Before building, you need to create a local `.env` file. You can simply copy the sample file provided in the repository.

   ```bash
   cp .env.sample .env
   ```

2. **Build the Docker Image:**
   Build the Docker image using the `runtime` target. You can specify a custom image name, tag, and an optional `BUILD_ID` as a build argument.

   Ensure `DOCKER_BUILDKIT=1` is exported in your environment or prepended to the command:

   ```bash
   DOCKER_BUILDKIT=1 docker build --target runtime \
     --build-arg BUILD_ID="<your-build-id>" \
     -t <image-name>:<image-tag> .
   ```

3. **(Optional) Save Artifact for CI/CD:**
   If you are building in a pipeline and need to publish the image as an artifact, you can save the Docker image to a compressed tar archive:
   ```bash
   DOCKER_BUILDKIT=1 docker save <image-name>:<image-tag> | gzip > survey-designer-backend.tar.gz
   ```
