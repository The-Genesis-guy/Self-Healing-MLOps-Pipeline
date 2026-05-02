# Future Roadmap: Layer 3 & Beyond

With the Core Engine (Layer 1) and the FastAPI Backend (Layer 2) completely finished and tested on the 6.3 Million row PaySim dataset, the backend architecture is highly robust, self-healing, and domain-agnostic.

The remaining roadmap is entirely focused on the User Interface (Layer 3) and Production Deployment.

## 1. Layer 3: The React Dashboard
Currently, the pipeline's intelligence is only visible in the terminal or via raw JSON from the FastAPI endpoints. The next phase is to build a sleek, visual Command Center.

**Tech Stack:**
*   **React** (Frontend Framework)
*   **Vite** (Build Tool)
*   **TailwindCSS** (Styling)
*   **Recharts** (Data Visualization)

**Core Dashboard Features:**
1.  **System Status Banner:** Green (Healthy), Yellow (Drift Detected), Red (Retrain Suppressed).
2.  **Live PSI Line Chart:** A visual graph of the Population Stability Index over time, showing exactly when the data drifts.
3.  **Model Version Timeline:** A visual timeline showing the active model (e.g., `v1.pkl`), when `v2.pkl` was rejected by the Guardian Gate, and when `v5.pkl` was successfully promoted.
4.  **Manual Overrides:** Buttons to trigger the `POST /pipeline/start` and `POST /pipeline/stop` API endpoints to control the background simulation directly from the browser.

## 2. Production Deployment
Once the UI is built, the entire project will be dockerized.

**Docker Compose Architecture:**
*   `backend`: Runs the FastAPI server (`uvicorn`).
*   `frontend`: Runs the React application.
*   `db`: Currently using local SQLite for portability, but can be scaled to PostgreSQL if required.

## 3. Academic Reporting
A 50+ page technical document will be generated detailing the software engineering principles used:
*   **Open-Closed Principle:** How the Adapter pattern allowed the Kaggle dataset to be integrated without changing the core code.
*   **Algorithmic Safety:** How the Guardian Gate and Retrain Capper prevent infinite loops and degraded performance in autonomous systems.
*   **Memory Management:** How the `DataStreamer` processes 500MB of data using 100k-row chunking algorithms.
