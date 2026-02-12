import axios from 'axios';

const API_BASE = '/api';

const client = axios.create({
  baseURL: API_BASE,
  timeout: 300000, // 5 min — LLM calls can be slow
});

/**
 * Generate a DDR report from two uploaded documents.
 *
 * @param {File} inspectionFile - The inspection report file (PDF/TXT).
 * @param {File} thermalFile    - The thermal report file (PDF/TXT).
 * @returns {Promise<object>}   - The DDR response payload.
 */
export async function generateDDR(inspectionFile, thermalFile) {
  const formData = new FormData();
  formData.append('inspection_file', inspectionFile);
  formData.append('thermal_file', thermalFile);

  const response = await client.post('/generate-ddr', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

  return response.data;
}
