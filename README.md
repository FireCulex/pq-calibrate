# 🧪 HDR PQ Calibrator

This tool takes user-defined PQ measurements, calibrates the EOTF, and hands off corrected data to ArgyllCMS for LUT generation and profiling—producing accurate, tonemapping-free HDR.

I built it to address HDR calibration challenges on Windows 11 that couldn’t be solved via display menu settings alone. My Hisense U6G, for example, overshoots the PQ curve and applies internal tonemapping, which results in washed-out highlights and degraded contrast.

## ⚙️ Calibration Workflow

This section outlines the step-by-step process to calibrate your HDR display and generate a custom ICC profile. 

In this example I use Dogegen and HCFR.

### 1. Grayscale Measurements

Begin by taking precise grayscale measurements of your HDR display. 

* **Launch HDR patterns using Dogegen:**

    ```
    dogegen.exe pgen_hdr
    ```

* **In HCFR:**

    * Select "Raspberry Pi" as the pattern generator (Dogegen emulates this).
      
    * Save the grayscale measurements to a file named `eotf_measurements.json`.

### 2. Run PQ Calibration Script

Process the collected measurements using your custom Python calibrator script. This step analyzes the EOTF data and prepares it for profile generation.

```
python pq_calibrator.py
```

### 3. Generate Target Chart
Create synthetic color patches that ArgyllCMS will use to measure the display's response across its color space.
```
targen -v -d3 -g20 "chart"
```

### 4. Measure Display Response
Utilize your generated calibration file to measure the display's response against the target chart.
```
dispread -v -k "pq_600nits.cal" "chart"
```

### 5. Create ICC Profile
Build the final HDR ICC profile using the measured display data.
```
colprof -v -A "My_HDR_Display" -o "My_HDR_Display.icc" "chart"
```

### 6. Install Profile
Activate the newly created ICC profile on your primary display.
```
dispwin -I -d1 My_HDR_Display.icc
```

Note : Windows 11 may not automatically load your HDR ICC profile. To ensure consistent application it is recommended to set up a startup task.

## 🛠️ Required Tools

This workflow relies on the following essential software:

* **HCFR:** Free calibration software for color analysis.

    * [HCFR HDR GUIDE](https://www.avsforum.com/threads/hcfr-guide-for-hdr-pq-eotf-graph-measurements.3278618/)

* **Dogegen:** HDR/SDR test pattern generator.

    * [Dogegen GitHub](https://github.com/ledoge/dogegen)

* **ArgyllCMS:** ICC profiling and calibration toolkit.

    * [ArgyllCMS Homepage](http://www.argyllcms.com/index.html)
