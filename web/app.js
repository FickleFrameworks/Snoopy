/* Subtle particle network for dark glassmorphism theme */

particlesJS('particles-js',
  {
    "particles": {
      "number": {
        "value": 40,
        "density": {
          "enable": true,
          "value_area": 1200
        }
      },
      "color": {
        "value": ["#648cff", "#8a2be2", "#00d2d3"]
      },
      "shape": {
        "type": "circle"
      },
      "opacity": {
        "value": 0.25,
        "random": true,
        "anim": {
          "enable": true,
          "speed": 0.3,
          "opacity_min": 0.08,
          "sync": false
        }
      },
      "size": {
        "value": 3,
        "random": true,
        "anim": {
          "enable": false
        }
      },
      "line_linked": {
        "enable": true,
        "distance": 160,
        "color": "#648cff",
        "opacity": 0.08,
        "width": 1
      },
      "move": {
        "enable": true,
        "speed": 0.3,
        "direction": "none",
        "random": true,
        "straight": false,
        "out_mode": "out",
        "attract": {
          "enable": false
        }
      }
    },
    "interactivity": {
      "detect_on": "canvas",
      "events": {
        "onhover": {
          "enable": true,
          "mode": "grab"
        },
        "onclick": {
          "enable": false
        },
        "resize": true
      },
      "modes": {
        "grab": {
          "distance": 140,
          "line_linked": {
            "opacity": 0.2
          }
        }
      }
    },
    "retina_detect": true
  }
);
