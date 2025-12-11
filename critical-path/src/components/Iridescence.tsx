import { useEffect, useRef } from 'react';
import { Color, Mesh, Program, Renderer, Triangle } from 'ogl';

const vertexShader = `
attribute vec2 uv;
attribute vec2 position;
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = vec4(position, 0, 1);
}
`;

const fragmentShader = `
precision highp float;
uniform float uTime;
uniform vec3 uColor;
uniform vec3 uResolution;
uniform vec2 uMouse;
uniform float uAmplitude;
uniform float uSpeed;
varying vec2 vUv;
void main() {
  float mr = min(uResolution.x, uResolution.y);
  vec2 uv = (vUv * 2.0 - 1.0) * uResolution.xy / mr;
  float d = -uTime * 0.5 * uSpeed;
  float a = 0.0;
  for (float i = 0.0; i < 8.0; ++i) {
    a += cos(i - d - a * uv.x);
    d += sin(uv.y * i + a);
  }
  vec3 col = vec3(cos(uv * vec2(d, a)) * 0.6 + 0.4, cos(a + d) * 0.5 + 0.5);
  col = cos(col * cos(vec3(d, a, 2.5)) * 0.5 + 0.5) * uColor;
  gl_FragColor = vec4(col, 1.0);
}
`;

interface IridescenceProps {
  color?: [number, number, number];
  speed?: number;
  amplitude?: number;
  animationState?: 'idle' | 'listening' | 'thinking' | 'responding';
}

export default function Iridescence({ 
  color = [0.3, 0.6, 1], 
  speed = 0.1, 
  amplitude = 0.1,
  animationState = 'idle'
}: IridescenceProps) {
  const container = useRef<HTMLDivElement | null>(null);
  const programRef = useRef<Program | null>(null);
  const rendererRef = useRef<Renderer | null>(null);
  const mountedRef = useRef(false);
  
  // Refs for smooth transitions
  const currentColorRef = useRef<[number, number, number]>(color);
  const targetColorRef = useRef<[number, number, number]>(color);
  const currentSpeedRef = useRef(speed);
  const targetSpeedRef = useRef(speed);
  const currentAmplitudeRef = useRef(amplitude);
  const targetAmplitudeRef = useRef(amplitude);

  useEffect(() => {
    if (!container.current || mountedRef.current) return;
    mountedRef.current = true;

    const renderer = new Renderer({ alpha: false, antialias: true });
    rendererRef.current = renderer;
    const { gl } = renderer;
    const geometry = new Triangle(gl);
    
    // Get container size
    const size = container.current.clientWidth || 200;
    
    const program = new Program(gl, {
      vertex: vertexShader,
      fragment: fragmentShader,
      uniforms: {
        uTime: { value: 0 },
        uColor: { value: new Color(color[0], color[1], color[2]) },
        uResolution: { 
          value: new Color(size, size, 1.0) 
        },
        uMouse: { value: [0.5, 0.5] },
        uAmplitude: { value: amplitude },
        uSpeed: { value: speed },
      },
    });

    const mesh = new Mesh(gl, { geometry, program });
    
    // Set renderer size
    renderer.setSize(size, size);
    gl.canvas.style.width = '100%';
    gl.canvas.style.height = '100%';
    gl.canvas.style.display = 'block';
    gl.canvas.style.pointerEvents = 'none'; // Allow clicks to pass through

    let animationId: number;
    let animationTime = 0;
    let lastFrameTime = 0;
    
    const animate = (t: number) => {
      if (!mountedRef.current) return;
      
      // Calculate delta time (capped to prevent large jumps)
      const deltaTime = lastFrameTime === 0 ? 16 : Math.min(t - lastFrameTime, 100);
      lastFrameTime = t;
      animationTime += deltaTime;
      
      // Smooth transition for color
      currentColorRef.current[0] += (targetColorRef.current[0] - currentColorRef.current[0]) * 0.08;
      currentColorRef.current[1] += (targetColorRef.current[1] - currentColorRef.current[1]) * 0.08;
      currentColorRef.current[2] += (targetColorRef.current[2] - currentColorRef.current[2]) * 0.08;
      
      // Smooth transition for speed
      currentSpeedRef.current += (targetSpeedRef.current - currentSpeedRef.current) * 0.08;
      
      // Smooth transition for amplitude (with pulsing for thinking state)
      let targetAmp = targetAmplitudeRef.current;
      if (animationState === 'thinking') {
        targetAmp += Math.sin(animationTime * 0.005) * 0.15;
      }
      currentAmplitudeRef.current += (targetAmp - currentAmplitudeRef.current) * 0.08;
      
      // Update uniforms using delta-based time
      program.uniforms.uTime.value = animationTime * 0.001;
      program.uniforms.uColor.value = new Color(
        currentColorRef.current[0],
        currentColorRef.current[1],
        currentColorRef.current[2]
      );
      program.uniforms.uSpeed.value = currentSpeedRef.current;
      program.uniforms.uAmplitude.value = currentAmplitudeRef.current;
      
      renderer.render({ scene: mesh });
      animationId = requestAnimationFrame(animate);
    };
    animate(0);

    if (container.current) {
      container.current.appendChild(gl.canvas);
    }
    programRef.current = program;

    // Handle resize
    const handleResize = () => {
      if (container.current && mountedRef.current) {
        const newSize = container.current.clientWidth || 200;
        renderer.setSize(newSize, newSize);
        program.uniforms.uResolution.value = new Color(newSize, newSize, 1.0);
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      mountedRef.current = false;
      cancelAnimationFrame(animationId);
      window.removeEventListener('resize', handleResize);
      if (gl.canvas.parentNode) {
        gl.canvas.parentNode.removeChild(gl.canvas);
      }
      gl.getExtension('WEBGL_lose_context')?.loseContext();
    };
  }, []);

  // Update uniforms when props change
  useEffect(() => {
    if (programRef.current) {
      // Update target values for smooth transition
      targetColorRef.current = [color[0], color[1], color[2]];
      targetSpeedRef.current = speed;
      targetAmplitudeRef.current = amplitude;
    }
  }, [amplitude, speed, color, animationState]);

  return <div ref={container} className="w-full h-full" />;
}
