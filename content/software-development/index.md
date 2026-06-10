---
title: "Software"
hideTitle: true
---

I spend most of my time working in Python, C++, and CUDA, with a healthy dose of Rust. I've previously worked in a variety of other languages including Java, JavaScript, PHP, SQL, and Go.

Most recently, I gave a talk at PyCon 2026 on the basics of GPU computing for Python developers and data/AI scientists. You can view the slides below:

<div class="cv-embed">
  <iframe src="PyCon2026.pdf" title="PyCon 2026 Talk" loading="lazy" style="height: 600px;"></iframe>
</div>

<div class="video-grid">
  <div class="video-card">
    <div class="video-embed">
      <iframe
        src="https://www.youtube.com/embed/u74pWKndzqE?si=Sgl403k-iK6e-6mM"
        title="Polars SF Meetup"
        frameborder="0"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowfullscreen
      ></iframe>
    </div>
  </div>
  <div class="video-card">
    <div class="video-embed">
      <iframe
        src="https://www.youtube.com/embed/2omzi5S6WV4?si=PTih_T5rBDQl-oRg"
        title="DataFrames at SciPy 2025"
        frameborder="0"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowfullscreen
      ></iframe>
    </div>
  </div>
</div>

## Projects

### cuDF & DataFrames

My primary work at NVIDIA is on [cuDF](https://github.com/rapidsai/cudf/), a GPU-accelerated DataFrame library built on [Apache Arrow](https://github.com/apache/arrow). We've built accelerated backends for both [pandas](https://github.com/pandas-dev/pandas) and [Polars](https://github.com/pola-rs/polars), enabling users to speed up their existing DataFrame workflows on GPUs with minimal code changes.

### RAPIDS

Beyond cuDF, I'm a significant contributor to other libraries in the [RAPIDS](https://github.com/rapidsai/) ecosystem including [cuML](https://github.com/rapidsai/cuml) (machine learning), [cuGraph](https://github.com/rapidsai/cugraph) (graph analytics), [RMM](https://github.com/rapidsai/rmm) (memory management), and [cuVS](https://github.com/rapidsai/cuvs) (vector search).
### Python Build & Packaging

I'm deeply involved in the Python build tooling ecosystem. I contribute to [scikit-build-core](https://github.com/scikit-build/scikit-build-core), the modern Python-CMake build adapter, and created [rapids-build-backend](https://github.com/rapidsai/rapids-build-backend), a PEP 517 build backend for managing complex native Python packages. I'm also a core developer of [native-lib-loader](https://native-lib-loader.readthedocs.io/en/latest/), a tool for loading platform-specific native libraries from Python wheels that is designed for use by any project. I've also contributed to [Cython](https://github.com/cython/cython) itself.

### CMake

I maintain [rapids-cmake](https://github.com/rapidsai/rapids-cmake), a collection of CMake modules that simplify building CUDA-accelerated C++ projects. I have extensive experience with CMake and have also made contributions to [upstream CMake](https://gitlab.kitware.com/cmake/cmake).

### Other CUDA Contributions

I've contributed to a number of other core open-source projects in the CUDA ecosystem including [NVIDIA CCCL](https://github.com/NVIDIA/cccl) (CUDA C++ Core Libraries) and [cuda-python](https://github.com/NVIDIA/cuda-python) (Python bindings for CUDA).

### Scientific Software

As part of my PhD research I became actively involved in the development of a great deal of scientific software including [signac](http://signac.io) and [freud](http://freud.readthedocs.io), both of which I have also previously presented on at SciPy:

<div class="video-grid">
  <div class="video-card">
    <div class="video-embed">
      <iframe
        src="https://www.youtube.com/embed/D0LWh1BzPRQ"
        title="freud at SciPy 2019"
        frameborder="0"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowfullscreen
      ></iframe>
    </div>
    <p class="video-caption">My colleague Bradley Dice and I presenting freud at SciPy 2019</p>
  </div>
  <div class="video-card">
    <div class="video-embed">
      <iframe
        src="https://www.youtube.com/embed/CCKQH1M2uR4"
        title="freud at SciPy 2018"
        frameborder="0"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowfullscreen
      ></iframe>
    </div>
    <p class="video-caption">Me presenting freud at SciPy 2018</p>
  </div>
</div>

In graduate school my colleague Simon Adorf and I published [a paper](https://ieeexplore.ieee.org/document/8558687) on this topic in [Computing in Science & Engineering](https://www.computer.org/csdl/magazine/cs), and more recently we wrote a [blog post](https://bssw.io/blog_posts/the-lazy-approach-to-developing-scientific-research-software) providing a high level discussion of our approach. In that vein I developed a few small, self-contained Python packages with clear applications: the [rowan](http://rowan.readthedocs.io/) package for quaternion manipulation and the [coxeter](http://coxeter.readthedocs.io/) package for working with geometric data, particularly polytopes in two and three dimensions. I was also a core developer for [HOOMD-blue](http://glotzerlab.engin.umich.edu/hoomd-blue/), a high-performance particle simulation engine that scales from single CPUs to leadership-class GPU supercomputers and is one of NVIDIA's official HPC benchmarks.
