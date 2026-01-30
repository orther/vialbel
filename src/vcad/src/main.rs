//! Vial label applicator components built with vcad.
//!
//! Generates simplified versions of each component as STL and GLB files.
//! These lack BREP fillets (vcad is mesh-based) but are suitable for
//! Blender MCP import and rapid prototyping.

mod frame;
mod peel_plate;
mod vial_cradle;

fn main() {
    let output_dir = "../../models/vcad";
    std::fs::create_dir_all(output_dir).expect("Failed to create output directory");

    println!("Building vcad components...\n");

    let plate = peel_plate::build();
    let plate_path = format!("{}/peel_plate.stl", output_dir);
    plate
        .write_stl(&plate_path)
        .expect("Failed to write peel plate STL");
    println!("Exported: {}", plate_path);

    let cradle = vial_cradle::build();
    let cradle_path = format!("{}/vial_cradle.stl", output_dir);
    cradle
        .write_stl(&cradle_path)
        .expect("Failed to write vial cradle STL");
    println!("Exported: {}", cradle_path);

    let frame = frame::build();
    let frame_path = format!("{}/main_frame.stl", output_dir);
    frame
        .write_stl(&frame_path)
        .expect("Failed to write main frame STL");
    println!("Exported: {}", frame_path);

    println!("\nAll vcad components built.");
}
