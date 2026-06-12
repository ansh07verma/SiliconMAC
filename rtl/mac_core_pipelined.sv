module mac_core_pipelined #(
    parameter int WIDTH = 8,
    parameter int ARRAY_SIZE = 4,
    parameter int PIPELINE_DEPTH = 2
)(
    input  logic                                    clk,
    input  logic                                    rst_n,
    input  logic                                    start,
    input  logic [WIDTH*ARRAY_SIZE-1:0]             operand_a,
    input  logic [WIDTH*ARRAY_SIZE-1:0]             operand_b,
    output logic [WIDTH*2+$clog2(ARRAY_SIZE)-1:0]   result,
    output logic                                    done,
    output logic                                    overflow,
    output logic                                    zero
);

    localparam int ACC_WIDTH = WIDTH * 2 + $clog2(ARRAY_SIZE);

    typedef enum logic [1:0] { IDLE, ACCUM, DONE_S } state_t;

    state_t state, next_state;
    logic [ACC_WIDTH-1:0] accumulator, next_accumulator;
    int unsigned idx, next_idx;

    logic [WIDTH-1:0] a_slice, b_slice;
    logic [WIDTH*2-1:0] product;

    always_comb begin
        a_slice = operand_a[idx*WIDTH +: WIDTH];
        b_slice = operand_b[idx*WIDTH +: WIDTH];
    end

    generate
        if (PIPELINE_DEPTH >= 1) begin
            logic [WIDTH*2-1:0] pipe [PIPELINE_DEPTH-1:0];
            always_ff @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    for (int p = 0; p < PIPELINE_DEPTH; p++) pipe[p] <= '0;
                end else begin
                    pipe[0] <= a_slice * b_slice;
                    for (int p = 1; p < PIPELINE_DEPTH; p++) pipe[p] <= pipe[p-1];
                end
            end
            assign product = pipe[PIPELINE_DEPTH-1];
        end else begin
            assign product = a_slice * b_slice;
        end
    endgenerate

    always_comb begin
        next_state = state;
        next_accumulator = accumulator;
        next_idx = idx;
        done = 1'b0;

        case (state)
            IDLE: begin
                next_accumulator = '0;
                next_idx = 0;
                if (start) next_state = ACCUM;
            end

            ACCUM: begin
                next_accumulator = accumulator + product;
                if (idx == ARRAY_SIZE - 1) begin
                    next_state = DONE_S;
                end else begin
                    next_idx = idx + 1;
                end
            end

            DONE_S: begin
                done = 1'b1;
                if (!start) next_state = IDLE;
            end
        endcase
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            accumulator <= '0;
            idx <= 0;
        end else begin
            state <= next_state;
            accumulator <= next_accumulator;
            idx <= next_idx;
        end
    end

    assign result = accumulator;
    assign overflow = (accumulator != '0) && (accumulator[ACC_WIDTH-1:ACC_WIDTH-2] == 2'b01);
    assign zero     = (accumulator == '0);

endmodule
