module silicon_npu #(
    parameter int WIDTH      = 8,
    parameter int ARRAY_SIZE = 4,
    parameter int DEPTH      = 4
)(
    input  logic                    clk,
    input  logic                    rst_n,
    input  logic                    start,
    input  logic [WIDTH-1:0]        weight_wr_data,
    input  logic [$clog2(DEPTH)-1:0]   weight_wr_row,
    input  logic [$clog2(ARRAY_SIZE)-1:0] weight_wr_col,
    input  logic                    weight_wr_en,
    input  logic [WIDTH-1:0]        act_wr_data,
    input  logic [$clog2(DEPTH)-1:0]   act_wr_row,
    input  logic [$clog2(ARRAY_SIZE)-1:0] act_wr_col,
    input  logic                    act_wr_en,
    output logic [WIDTH*2+$clog2(ARRAY_SIZE)+$clog2(DEPTH)-1:0] result,
    output logic                    done,
    output logic                    busy
);

    localparam int ACC_WIDTH = WIDTH * 2 + $clog2(ARRAY_SIZE) + $clog2(DEPTH);
    localparam int ROW_BITS  = $clog2(DEPTH);
    localparam int COL_BITS  = $clog2(ARRAY_SIZE);

    typedef enum logic [1:0] {
        IDLE    = 2'd0,
        COMPUTE = 2'd1,
        DONE_S  = 2'd2
    } state_t;

    state_t state;
    logic [ROW_BITS-1:0] row_idx;
    logic [ACC_WIDTH-1:0] accumulator;

    // Weight memory
    logic [WIDTH-1:0] weight_mem [0:DEPTH-1][0:ARRAY_SIZE-1];

    // Activation memory
    logic [WIDTH-1:0] act_mem [0:DEPTH-1][0:ARRAY_SIZE-1];

    // Weight memory write
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (int r = 0; r < DEPTH; r++)
                for (int c = 0; c < ARRAY_SIZE; c++)
                    weight_mem[r][c] <= '0;
        end else if (weight_wr_en) begin
            weight_mem[weight_wr_row][weight_wr_col] <= weight_wr_data;
        end
    end

    // Activation memory write
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (int r = 0; r < DEPTH; r++)
                for (int c = 0; c < ARRAY_SIZE; c++)
                    act_mem[r][c] <= '0;
        end else if (act_wr_en) begin
            act_mem[act_wr_row][act_wr_col] <= act_wr_data;
        end
    end

    // MAC computation: sum of (act[r][i] * weight[r][i]) for all i
    logic [ACC_WIDTH-1:0] mac_result;
    always_comb begin
        mac_result = '0;
        for (int i = 0; i < ARRAY_SIZE; i++) begin
            mac_result = mac_result +
                act_mem[row_idx][i] * weight_mem[row_idx][i];
        end
    end

    // State machine
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state       <= IDLE;
            row_idx     <= '0;
            accumulator <= '0;
        end else begin
            case (state)
                IDLE: begin
                    accumulator <= '0;
                    row_idx     <= '0;
                    if (start) state <= COMPUTE;
                end

                COMPUTE: begin
                    accumulator <= accumulator + mac_result;
                    if (row_idx == DEPTH - 1) begin
                        state <= DONE_S;
                    end else begin
                        row_idx <= row_idx + 1;
                    end
                end

                DONE_S: begin
                    if (!start) state <= IDLE;
                end

                default: state <= IDLE;
            endcase
        end
    end

    assign result = accumulator;
    assign done   = (state == DONE_S);
    assign busy   = (state != IDLE);

endmodule
